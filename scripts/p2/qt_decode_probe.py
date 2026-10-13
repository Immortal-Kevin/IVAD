"""Actual Qt Multimedia video decode; P2 precise PTS source remains PyAV."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.p2.make_samples import make_all
from PySide6.QtCore import QUrl,QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer,QVideoSink
samples=make_all(ROOT/'artifacts/p2/samples');app=QApplication([])
player=QMediaPlayer();sink=QVideoSink();player.setVideoSink(sink)
result={'source':'samples/sample.mp4','frames':0,'start_times_us':[],'errors':[]}
def frame(value):
    if value.isValid():result['frames']+=1;result['start_times_us'].append(value.startTime())
def done():
    result.update(duration_ms=player.duration(),status='PASS' if result['frames'] else 'FAIL',qt_version=__import__('PySide6').__version__)
    player.stop();(ROOT/'artifacts/p2/qt-decode.json').write_text(json.dumps(result,indent=2),encoding='utf-8');app.quit()
sink.videoFrameChanged.connect(frame);player.errorOccurred.connect(lambda error,message:result['errors'].append(message))
player.setSource(QUrl.fromLocalFile(str(samples/'sample.mp4')));player.play();QTimer.singleShot(4000,done)
app.exec()
raise SystemExit(0 if result['frames'] else 1)
