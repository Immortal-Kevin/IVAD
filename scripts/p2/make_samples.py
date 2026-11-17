"""自制可复现工程测试录像，不包含厂区或第三方素材。"""
import sys, json, struct
from pathlib import Path
from fractions import Fraction
import av
import numpy as np
from PIL import Image, ImageDraw

def make_video(path, *, seed=0, codec='libx264', variable=False, rate=Fraction(25,1)):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    time_base = Fraction(1,1000) if variable else Fraction(rate.denominator, rate.numerator)
    pts = [i if not variable else sum(40 if j%3 else 120 for j in range(i)) for i in range(36)]
    with av.open(str(path), 'w') as output:
        stream = output.add_stream(codec, rate=rate)
        stream.width = 320; stream.height = 180; stream.pix_fmt = 'yuv420p'
        stream.time_base = time_base; stream.codec_context.time_base = time_base
        if codec == 'libx264': stream.options = {'bf':'2','g':'12','crf':'18'}
        for i, timestamp in enumerate(pts):
            image = Image.new('RGB',(320,180),(30+seed*20,40,65))
            draw = ImageDraw.Draw(image); draw.rectangle((10+i*5%220,70,70+i*5%220,140), fill=(220,110+seed*10,40))
            draw.text((12,12),f'IVAD owned test {seed} frame {i}',fill='white')
            draw.rectangle((0,0,8,8),fill=(255,0,0))
            frame = av.VideoFrame.from_ndarray(np.asarray(image),format='rgb24'); frame.pts=timestamp; frame.time_base=time_base
            for packet in stream.encode(frame): output.mux(packet)
        for packet in stream.encode(): output.mux(packet)
    return path

def rotate_owned_mp4(source, destination):
    data = bytearray(Path(source).read_bytes())
    # 自制测试MP4的tkhd display matrix；不操作用户录像。
    index = data.index(b'tkhd'); payload = index+4
    version = data[payload]
    matrix = payload+(52 if version == 1 else 40)
    struct.pack_into('>9i',data,matrix,0,65536,0,-65536,0,0,0,0,1073741824)
    Path(destination).write_bytes(data)

def make_all(directory):
    directory = Path(directory); directory.mkdir(parents=True,exist_ok=True)
    for name, codec, seed in [('sample.mp4','libx264',0),('sample.avi','mpeg4',1),('sample.mov','libx264',2),('sample.mkv','libx264',3)]: make_video(directory/name,codec=codec,seed=seed)
    make_video(directory/'vfr.mp4',variable=True,seed=4)
    make_video(directory/'noninteger.mp4',rate=Fraction(30000,1001),seed=5)
    rotate_owned_mp4(directory/'sample.mp4',directory/'rotation.mp4')
    (directory/'corrupt.mp4').write_bytes(b'IVAD intentionally damaged test file')
    return directory

if __name__ == '__main__': make_all(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'artifacts/p2/samples')
