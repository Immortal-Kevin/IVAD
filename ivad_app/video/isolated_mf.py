"""Bounded local MF decoder protocol v1; native crashes cannot kill the GUI.

No network, pickle, legacy decoder fallback or persistent preview cache.
Only this object's owned worker tree may be terminated on cancel/timeout.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import struct
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ivad_app.video.windows_mf import SourceReader, VideoFrame

VERSION='ivad-mf-pipe-v1'
MAX_PIXELS=128*1024*1024

def _send(message, pixels=b''):
    header=json.dumps(dict(message,protocol=VERSION,pixel_bytes=len(pixels)),allow_nan=False).encode('utf8')
    sys.stdout.buffer.write(struct.pack('<I',len(header)))
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(pixels)
    sys.stdout.buffer.flush()

def _worker(path):
    try:
        with SourceReader(path) as reader:
            _send(dict(kind='metadata',container=reader.container,codec=reader.codec,width=reader.width,height=reader.height,
                       frame_rate=reader.frame_rate,duration_ticks=reader.duration_ticks,rotation=reader.rotation))
            for frame in reader.frames():
                _send(dict(kind='frame',pts=frame.pts,width=frame.width,height=frame.height,stride=frame.stride),frame.pixels)
            _send(dict(kind='end'))
        return 0
    except Exception as exc:
        _send(dict(kind='error',message=str(exc)))
        return 1

def _exact(pipe, length):
    chunks=[]
    while length:
        chunk=pipe.read(length)
        if not chunk:raise EOFError('Native media worker closed the stream')
        chunks.append(chunk);length-=len(chunk)
    return b''.join(chunks)

class IsolatedSourceReader:
    def __init__(self,path,*,timeout=20.0):
        self.timeout=timeout
        self.closed=False
        self.stop=threading.Event()
        self.messages=queue.Queue(maxsize=2)
        self.worker=subprocess.Popen([sys.executable,'-I','-X','utf8',str(Path(__file__).resolve()),str(Path(path).resolve(strict=True))],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.thread=threading.Thread(target=self._pump,daemon=True)
        self.thread.start()
        try:
            metadata,_=self._receive(lambda:None)
            if metadata.get('kind')!='metadata':raise ValueError('Expected MF metadata')
            for name in ('container','codec','width','height','frame_rate','duration_ticks','rotation'):
                setattr(self,name,metadata[name])
        except BaseException:
            self.close();raise

    def _put(self,item):
        while not self.stop.is_set():
            try:self.messages.put(item,timeout=.1);return
            except queue.Full:pass

    def _pump(self):
        try:
            while not self.stop.is_set():
                size=struct.unpack('<I',_exact(self.worker.stdout,4))[0]
                if not 0<size<=65536:raise ValueError('Invalid native media protocol header')
                message=json.loads(_exact(self.worker.stdout,size))
                size=message.get('pixel_bytes',-1)
                if message.get('protocol')!=VERSION or not isinstance(size,int) or not 0<=size<=MAX_PIXELS:
                    raise ValueError('Invalid native media protocol payload')
                pixels=_exact(self.worker.stdout,size)
                self._put((message,pixels))
                if message.get('kind') in {'end','error'}:return
        except BaseException as exc:
            self._put(exc)

    def _receive(self,check):
        deadline=time.monotonic()+self.timeout
        while not self.closed:
            check()
            if time.monotonic()>deadline:raise TimeoutError('Windows decoder response timed out')
            try:item=self.messages.get(timeout=.05)
            except queue.Empty:continue
            if isinstance(item,BaseException):raise RuntimeError(f'Native media worker failed (exit={self.worker.poll()}): {item}') from item
            if item[0].get('kind')=='error':raise RuntimeError(item[0].get('message','Native decoder error'))
            return item
        raise RuntimeError('Media reader is closed')

    def frames(self,check=lambda:None):
        while True:
            message,pixels=self._receive(check)
            kind=message.get('kind')
            if kind=='end':return
            if kind!='frame':raise ValueError('Unexpected MF message')
            width,height,stride=message['width'],message['height'],message['stride']
            if not isinstance(message['pts'],int) or not 0<width<=16384 or not 0<height<=16384 or stride!=width*4 or len(pixels)!=stride*height:
                raise ValueError('Invalid frame dimensions or timestamp')
            yield VideoFrame(message['pts'],width,height,stride,pixels)

    def close(self):
        if self.closed:return
        self.closed=True;self.stop.set()
        if self.worker.poll() is None:
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(self.worker.pid),'/T','/F'],capture_output=True,timeout=10,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            else:self.worker.terminate()
        self.worker.wait(timeout=10)
        self.thread.join(timeout=3)
        self.worker.stdout.close()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()

if __name__=='__main__':raise SystemExit(_worker(sys.argv[1]))
