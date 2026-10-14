"""真实画面播放器，解码在线程；时间轴/逐帧以实际PTS定位。"""
import queue, threading, time
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QSlider,QComboBox,QDoubleSpinBox
from ivad_app.gui.pages import button
from ivad_app.video.reader import FileVideoSource
from ivad_app.core.contracts import AppError

def qimage(pil):
    image=pil.convert('RGB');return QImage(image.tobytes(),image.width,image.height,image.width*3,QImage.Format.Format_RGB888).copy()

class VideoPlayer(QWidget):
    decoded=Signal(object)
    failed=Signal(str)
    capture_requested=Signal(int)
    def __init__(self):
        super().__init__();self.position_us=0;self.duration_us=0;self.playing=False;self.last_image=None;self.loaded=False;self.generation=0
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.picture=QLabel('选择录像后显示实际画面');self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter);self.picture.setMinimumHeight(120);self.picture.setStyleSheet('background:#172435;color:white;');layout.addWidget(self.picture,1)
        self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.setObjectName('video_timeline');self.slider.sliderReleased.connect(lambda:self.seek(self.slider.value()*1000));layout.addWidget(self.slider)
        row=QHBoxLayout();self.play_button=button('播放',self.toggle,name='video_play');self.previous=button('上一帧',lambda:self.command('step',-1),name='video_previous');self.next=button('下一帧',lambda:self.command('step',1),name='video_next')
        self.speed=QComboBox();self.speed.addItems(['0.25×','0.5×','1×','2×','4×']);self.speed.setCurrentIndex(2);self.speed.currentTextChanged.connect(lambda text:self.command('speed',float(text[:-1])))
        self.goto=QDoubleSpinBox();self.goto.setDecimals(3);self.goto.setSuffix(' 秒');self.goto.setRange(0,10000000)
        self.capture_button=button('当前画面候选帧',lambda:self.capture_requested.emit(self.position_us),name='capture_frame')
        self.goto_button=button('跳转',lambda:self.seek(round(self.goto.value()*1000000)))
        for widget in [self.previous,self.play_button,self.next,self.speed]:row.addWidget(widget)
        layout.addLayout(row);row=QHBoxLayout()
        for widget in [self.goto,self.goto_button,self.capture_button]:row.addWidget(widget)
        layout.addLayout(row);self.info=QLabel('PTS尚未加载');layout.addWidget(self.info)
        self.commands=queue.Queue();self.thread=threading.Thread(target=self.worker,name='IVAD-P2-Video',daemon=False);self.thread.start()
        self.decoded.connect(self.show_frame);self.failed.connect(self.show_error);self.set_controls(False)

    def set_controls(self,enabled):
        for widget in [self.play_button,self.previous,self.next,self.speed,self.goto,self.slider,self.capture_button,self.goto_button]:widget.setEnabled(enabled)
    def command(self,name,value=None):self.commands.put((name,value))
    def load(self,path,metadata):
        self.stop();self.loaded=True;self.duration_us=metadata['duration_us'];self.slider.setRange(0,max(1,self.duration_us//1000));self.goto.setMaximum(self.duration_us/1000000);self.command('load',(path,metadata,self.generation))
    def stop(self):
        self.generation+=1;self.playing=False;self.play_button.setText('播放');self.command('reset');self.set_controls(False);self.loaded=False;self.position_us=0;self.last_image=None;self.picture.clear();self.picture.setText('选择录像后显示实际画面')
    def toggle(self):
        self.playing=not self.playing;self.play_button.setText('暂停' if self.playing else '播放');self.command('play',self.playing)
    def seek(self,microseconds):self.playing=False;self.play_button.setText('播放');self.command('seek',int(microseconds))
    @Slot(object)
    def show_frame(self,value):
        generation,frame=value
        if not self.loaded or generation!=self.generation:return
        if frame is None:self.playing=False;self.play_button.setText('播放');return
        self.set_controls(True)
        self.position_us=frame.time_us;self.last_image=qimage(frame.image);self.display()
        if not self.slider.isSliderDown():self.slider.setValue(max(0,frame.time_us//1000))
        self.info.setText(f'当前位置 {frame.time_us/1000000:.3f} / {self.duration_us/1000000:.3f} 秒 · 实际PTS {frame.pts_us} µs · {frame.image.width}×{frame.image.height}')
    def display(self):
        if self.last_image:self.picture.setPixmap(QPixmap.fromImage(self.last_image).scaled(self.picture.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def resizeEvent(self,event):super().resizeEvent(event);self.display()
    def show_error(self,text):self.playing=False;self.play_button.setText('播放');self.info.setText(text)

    def worker(self):
        source=None;generator=None;current=None;playing=False;speed=1.0;generation=0
        def close_generator():
            nonlocal generator
            if generator:generator.close();generator=None
        while True:
            try:
                if playing and source:
                    try:name,value=self.commands.get_nowait()
                    except queue.Empty:
                        if generator is None:generator=source.iter_frames(current.time_us+1 if current else 0)
                        frame=next(generator,None)
                        if frame is None:playing=False;close_generator();self.decoded.emit((generation,None));continue
                        delay=max(0,(frame.time_us-(current.time_us if current else frame.time_us))/1000000/speed)
                        try:
                            name,value=self.commands.get(timeout=delay)
                            close_generator()
                        except queue.Empty:current=frame;self.decoded.emit((generation,frame));continue
                else:name,value=self.commands.get()
                if name=='close':close_generator();return
                if name=='reset':close_generator();source=None;current=None;playing=False;continue
                if name=='load':
                    close_generator();source=FileVideoSource(Path(value[0]),value[1]);generation=value[2];current=source.at(0);playing=False;self.decoded.emit((generation,current))
                elif name=='speed':speed=value
                elif name=='play':playing=value
                elif name in {'seek','step'} and source:
                    close_generator();playing=False
                    if name=='seek':current=source.at(value,before=True) if value>=source.metadata['duration_us'] else source.at(value)
                    elif value<0:current=source.at(current.time_us,before=True)
                    else:current=source.at(current.time_us+1)
                    self.decoded.emit((generation,current))
            except Exception as exc:
                playing=False;close_generator();self.failed.emit(exc.message if isinstance(exc,AppError) else '视频解码失败，请查看格式兼容性限制。')

    def shutdown(self):
        self.command('close');self.thread.join(timeout=15)
        if self.thread.is_alive():raise AppError('PLAYER_SHUTDOWN','视频解码尚未结束，请等待后重试关闭。')
