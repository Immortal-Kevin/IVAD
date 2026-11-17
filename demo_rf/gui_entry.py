"""Small independent offline GUI. CUDA is owned only by the separate worker."""
import sys
sys.dont_write_bytecode = True
if '--decode-worker' in sys.argv:
    sys.argv.remove('--decode-worker')
    from demo_rf.decode_entry import main as decode_main
    raise SystemExit(decode_main())
import csv
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import subprocess
import uuid
import time
import traceback
from PySide6.QtCore import Qt, QThread, Signal, QProcess, QTimer, QRectF, QStandardPaths, Slot, qInstallMessageHandler
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QDoubleSpinBox, QComboBox, QProgressBar,
    QListWidget, QSplitter, QMessageBox)

from demo_rf.diagnostics import install, record, exception

HERE = Path(__file__).resolve().parent
FROZEN = getattr(sys, 'frozen', False)
BASE = Path(sys.executable).parent if FROZEN else HERE.parent

def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    temporary.replace(path)

class Decode(QThread):
    sample = Signal(object)
    read_progress = Signal(int, float, float)
    completed = Signal(bool, int)
    failed = Signal(str)
    def __init__(self, video, interval, session, log_dir):
        super().__init__()
        self.video, self.interval, self.session, self.log_dir = video, interval, session, log_dir
        self.cancelled = threading.Event()
        self.resume = threading.Event(); self.resume.set()
        self.ack = threading.Event()
        self.decoded = 0; self.proc = None
    def stop(self):
        self.cancelled.set(); self.resume.set(); self.ack.set()
        if self.proc and self.proc.poll() is None:
            try: self.proc.terminate()
            except OSError: pass
    def run(self):
        complete = False
        try:
            args = [str(BASE/'IVAD_RF_Decode.exe'), '--decode-worker'] if FROZEN else [sys.executable, '-X', 'utf8', '-B', '-m', 'demo_rf.decode_entry']
            args += ['--video', str(self.video), '--interval', str(self.interval), '--session', str(self.session), '--log-dir', str(self.log_dir)]
            record(self.log_dir, 'gui', 'decode_launch', command=args)
            with (self.log_dir/'decode-stderr.log').open('ab') as err:
                if self.cancelled.is_set(): return
                self.proc = subprocess.Popen(args, cwd=str(BASE), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=err, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if self.cancelled.is_set(): self.stop()
                for line in self.proc.stdout:
                    data = json.loads(line.decode('utf8')); event = data['event']
                    if event == 'progress':
                        self.decoded = data['decoded']; self.read_progress.emit(self.decoded, data['seconds'], data['duration'])
                    elif event == 'sample':
                        self.decoded = data['decoded']; self.ack.clear(); self.sample.emit(data)
                        while not self.ack.wait(.1):
                            if self.cancelled.is_set(): break
                        while not self.resume.wait(.1):
                            if self.cancelled.is_set(): break
                        if self.cancelled.is_set(): self.stop(); break
                        self.proc.stdin.write(b'ack\n'); self.proc.stdin.flush()
                    elif event == 'complete': complete = True; self.decoded = data['decoded']
                    elif event == 'error': self.failed.emit(data['message'])
                code = self.proc.wait(timeout=5)
                record(self.log_dir, 'gui', 'decode_exit', code=code, hex=f'0x{code & 0xffffffff:08X}')
                if not self.cancelled.is_set() and (code != 0 or not complete):
                    self.failed.emit(f'视频解码子进程异常退出（{code} / 0x{code & 0xffffffff:08X}）。')
        except Exception as exc:
            exception(self.log_dir, 'gui', exc)
            if not self.cancelled.is_set(): self.failed.emit('视频解码通信失败：'+str(exc))
        finally:
            if self.proc:
                if self.proc.poll() is None:
                    self.proc.kill(); self.proc.wait(timeout=5)
                for pipe in (self.proc.stdin, self.proc.stdout):
                    if pipe: pipe.close()
            self.completed.emit(complete and not self.cancelled.is_set(), self.decoded)

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('IVAD RF-DETR Nano · 离线视频识别演示（本机候选）')
        self.resize(1260, 860)
        self.worker = None; self.decoder = None; self.session = None
        self.records = []; self.current_input = None; self.buffer = b''; self.probing = False
        self.outcome = 'NOT_STARTED'; self.gpu_info = {}; self.model_info = {}
        self.running = False; self.cancel_requested = False; self.closing = False
        self.gpu_forward_frames = 0; self.bounding_boxes_drawn = 0
        self.run_config = {}
        self.app_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.diagnostic = self.app_dir/'last-run.json'
        self.log_dir = install(self.app_dir/'diagnostics'/uuid.uuid4().hex, 'gui')
        self.worker_exit = None
        self.last_error = ''
        center = QWidget(); self.setCentralWidget(center); layout = QVBoxLayout(center)
        note = QLabel('实验模型 / 尚未经过现场验证。仅本地录像；不训练、不实时报警、不上传；不代表现场检测准确率。')
        note.setWordWrap(True); layout.addWidget(note)
        row = QHBoxLayout(); self.video = QLineEdit(); self.video.setObjectName('video_path')
        self.video.setPlaceholderText('请选择本地MP4视频')
        self.video_button = QPushButton('选择视频…'); self.video_button.clicked.connect(self.choose_video)
        row.addWidget(QLabel('本地视频')); row.addWidget(self.video, 1); row.addWidget(self.video_button); layout.addLayout(row)
        row = QHBoxLayout(); self.weights = QLineEdit(); self.weights.setObjectName('model_path')
        manifest = json.loads((BASE/'model_manifest.json' if FROZEN else HERE/'model_manifest.json').read_text(encoding='utf8'))
        self.manifest_path = BASE/'model_manifest.json' if FROZEN else HERE/'model_manifest.json'
        self.manifest = manifest
        self.model_choice = QComboBox(); self.model_choice.setObjectName('model_variant')
        for entry in manifest['models']:
            self.model_choice.addItem(entry.get('display_name', entry['filename']), entry['filename'])
        default = manifest.get('default_model', manifest['models'][0]['filename'])
        self.model_choice.setCurrentIndex(max(0, self.model_choice.findData(default)))
        row.addWidget(self.model_choice)
        self.model_button = QPushButton('选择模型…'); self.model_button.clicked.connect(self.choose_model)
        row.addWidget(QLabel('Nano权重')); row.addWidget(self.weights, 1); row.addWidget(self.model_button); layout.addLayout(row)
        self.model_summary = QLabel(); self.model_summary.setWordWrap(True); layout.addWidget(self.model_summary)
        self.model_choice.currentIndexChanged.connect(self.select_model_variant)
        self.select_model_variant(self.model_choice.currentIndex())
        row = QHBoxLayout()
        self.threshold = QDoubleSpinBox(); self.threshold.setRange(0, 1); self.threshold.setDecimals(3); self.threshold.setValue(.5)
        self.interval = QDoubleSpinBox(); self.interval.setRange(0, 3600); self.interval.setDecimals(3); self.interval.setSuffix(' 秒'); self.interval.setValue(1)
        self.resolution = QComboBox(); self.resolution.addItem('384（默认）', 384); self.resolution.addItem('320（低显存，须实测）', 320)
        for label, control in [('置信度阈值', self.threshold), ('采样间隔（0逐帧）', self.interval), ('模型输入', self.resolution)]:
            row.addWidget(QLabel(label)); row.addWidget(control)
        self.probe = QPushButton('检查GPU'); self.probe.clicked.connect(self.check_gpu); row.addWidget(self.probe)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.start_button = QPushButton('开始识别'); self.start_button.setObjectName('start_inference'); self.start_button.clicked.connect(self.start)
        self.pause_button = QPushButton('暂停'); self.pause_button.clicked.connect(self.pause); self.pause_button.setEnabled(False)
        self.cancel_button = QPushButton('取消任务'); self.cancel_button.clicked.connect(self.cancel); self.cancel_button.setEnabled(False)
        self.save_button = QPushButton('保存本地结果…'); self.save_button.clicked.connect(self.save); self.save_button.setEnabled(False)
        for b in [self.start_button, self.pause_button, self.cancel_button, self.save_button]: row.addWidget(b)
        layout.addLayout(row)
        self.gpu = QLabel('GPU：尚未检查。AI仅使用CUDA，不自动退回CPU。'); self.gpu.setWordWrap(True); layout.addWidget(self.gpu)
        self.status = QLabel('请选择录像和授权模型，然后开始识别。'); self.status.setObjectName('inference_status'); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.progress = QProgressBar(); layout.addWidget(self.progress)
        split = QSplitter(); self.frames = QListWidget(); self.frames.setObjectName('detected_frames'); self.frames.setMaximumWidth(360)
        self.frames.currentRowChanged.connect(self.show_frame); split.addWidget(self.frames)
        self.picture = QLabel('尚无新推理结果'); self.picture.setObjectName('detection_picture'); self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.picture.setMinimumSize(400, 280); self.picture.setStyleSheet('background:#172435;color:white;'); split.addWidget(self.picture)
        split.setSizes([300, 850]); layout.addWidget(split, 1)
        self.detail = QLabel('未推理帧不会显示为已检测。结果框使用原图像素坐标，显示时等比例缩放。'); self.detail.setWordWrap(True); layout.addWidget(self.detail)
        self.preview = None
    def choose_video(self):
        name, _ = QFileDialog.getOpenFileName(self, '选择本地录像', '', '本地视频 (*.mp4 *.mov *.mkv *.avi);;所有文件 (*)')
        if name: self.video.setText(name)
    def choose_model(self):
        name, _ = QFileDialog.getOpenFileName(self, '选择已授权RF-DETR Nano权重', str(BASE/'models'), 'RF-DETR权重 (*.pth)')
        if name:
            index = self.model_choice.findData(Path(name).name)
            self.model_choice.blockSignals(True); self.model_choice.setCurrentIndex(index); self.model_choice.blockSignals(False)
            self.weights.setText(name); self.update_model_summary()
    @Slot(int)
    def select_model_variant(self, index):
        if index < 0: return
        self.weights.setText(str(BASE/'models'/self.model_choice.itemData(index)))
        self.update_model_summary()
    def update_model_summary(self):
        index = self.model_choice.currentIndex()
        if index < 0:
            self.model_summary.setText('外部权重：加载时必须通过已登记SHA256及类别核对。'); return
        entry = self.manifest['models'][index]
        self.model_summary.setText(f"选定版本：{entry.get('display_name', entry['filename'])} · 示例数据集 v1 · 输入384 · 0 → 压滤版破裂。实验模型，尚未经过现场现场验证；加载时核对实际SHA256。")
    def controls(self, active):
        self.running = active
        for b in [self.start_button, self.video_button, self.model_button, self.model_choice, self.probe, self.threshold, self.interval, self.resolution, self.video, self.weights]: b.setEnabled(not active)
        self.cancel_button.setEnabled(active); self.pause_button.setEnabled(active and self.decoder is not None)
        self.save_button.setEnabled(not active and bool(self.records))
    def launch_worker(self, probe=False):
        self.buffer = b''; self.probing = probe
        self.worker = QProcess(self)
        self.worker.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.worker.readyReadStandardOutput.connect(self.read_worker)
        self.worker.readyReadStandardError.connect(self.log_worker)
        self.worker.finished.connect(self.worker_finished)
        self.worker.errorOccurred.connect(lambda e: self.fail('Worker进程错误：'+self.worker.errorString()) if e == QProcess.ProcessError.FailedToStart else None)
        if FROZEN:
            program = BASE/'worker'/'IVAD_RF_Worker.exe'; args = []
        else:
            program = BASE/'.venv-rfdetr/Scripts/python.exe'; args = ['-X','utf8','-B',str(HERE/'worker_entry.py')]
        args += ['--log-dir',str(self.log_dir), '--manifest',str(self.manifest_path)] + (['--probe'] if probe else [])
        self.worker.setProgram(str(program)); self.worker.setArguments(args)
        self.worker.started.connect(self.send_load if not probe else lambda:None)
        record(self.log_dir, 'gui', 'worker_launch', program=str(program), args=args)
        self.worker.start()
    def check_gpu(self):
        if self.running: return
        self.controls(True); self.status.setText('正在独立Worker检查驱动与CUDA…'); self.launch_worker(True)
    def start(self):
        if self.running: return
        if self.decoder and self.decoder.isRunning(): return
        if not Path(self.video.text()).is_file() or not Path(self.weights.text()).is_file():
            QMessageBox.information(self,'选择输入','请先选择存在的本地录像和授权Nano权重。'); return
        if self.session:
            shutil.rmtree(self.session)  # only this instance's tempfile.mkdtemp result
        self.session = Path(tempfile.mkdtemp(prefix='IVAD_RF_', dir=str(self.app_dir)))
        self.records = []; self.frames.clear(); self.preview = None; self.picture.setText('正在加载模型…')
        self.decoder = None; self.outcome = 'RUNNING'; self.cancel_requested = False
        self.model_info = {}; self.gpu_info = {}; self.gpu_forward_frames = self.bounding_boxes_drawn = 0
        self.worker_exit = None; self.last_error = ''; self.worker_modules = []
        self.run_config = dict(video=str(Path(self.video.text()).resolve()), threshold=self.threshold.value(),
                               sample_interval_seconds=self.interval.value(), resolution=self.resolution.currentData(),
                               model_selection=self.model_choice.currentText())
        self.progress.setValue(0); self.pause_button.setText('暂停'); self.controls(True)
        self.status.setText('正在加载已核验的RF-DETR Nano，界面可继续操作…'); self.launch_worker()
    def send(self, data):
        if self.worker and self.worker.state() == QProcess.ProcessState.Running:
            self.worker.write((json.dumps(data, ensure_ascii=False)+'\n').encode('utf8'))
    def send_load(self):
        self.send(dict(op='load', weights=self.weights.text(), resolution=self.resolution.currentData()))
    def read_worker(self):
        self.buffer += bytes(self.worker.readAllStandardOutput())
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n',1)
            if not line.strip(): continue
            try: self.worker_event(json.loads(line))
            except Exception as exc: self.fail('Worker结果无效：'+str(exc))
    def log_worker(self):
        data = bytes(self.worker.readAllStandardError())
        if data:
            with (self.log_dir/'worker-stderr.log').open('ab') as f: f.write(data)
    def worker_event(self, data):
        event = data['event']
        if event == 'gpu':
            self.gpu_info = data['gpu']; g = self.gpu_info
            self.gpu.setText(f"GPU：{g['name']} · Compute {g['compute_capability']} · 空闲{g['free_vram_bytes']/1024**3:.2f}GiB / {g['total_vram_bytes']/1024**3:.2f}GiB · Torch {g['torch']} / CUDA {g['torch_cuda']} · 驱动 {g['driver']}")
            if self.probing: self.status.setText('GPU环境检查完成；尚未加载模型或证明单帧推理。')
        elif event == 'loaded':
            self.model_info = data; self.status.setText(data['notice']+' 模型已加载CUDA，等待第一帧实际推理。')
            if self.cancel_requested: return
            record(self.log_dir, 'gui', 'model_loaded')
            self.decoder = Decode(Path(self.video.text()), self.interval.value(), self.session, self.log_dir)
            self.decoder.sample.connect(self.request_prediction); self.decoder.read_progress.connect(self.read_progress)
            self.decoder.failed.connect(self.fail); self.decoder.completed.connect(self.decode_complete)
            self.decoder.finished.connect(self.maybe_idle)
            self.pause_button.setEnabled(True); self.decoder.start()
        elif event == 'prediction':
            if self.cancel_requested: return
            if not self.current_input or data['frame_index'] != self.current_input['frame_index'] or not data['actual_inference']:
                raise ValueError('帧身份与实际推理状态不一致。')
            image = QImage(self.current_input['image'])
            if image.isNull(): raise ValueError('解码帧图像读取失败。')
            painter = QPainter(image)
            painter.setPen(QPen(QColor('#ffb000'), max(1, image.width()/400)))
            painter.setFont(QFont('Microsoft YaHei', max(8, round(image.width()/75))))
            for obj in data['objects']:
                x1,y1,x2,y2 = obj['xyxy']; painter.drawRect(QRectF(x1,y1,x2-x1,y2-y1))
                painter.drawText(round(x1), max(12,round(y1)), f"{obj['category']} {obj['confidence']:.3f}")
            painter.end()
            preview = self.session/f"frame-{data['frame_index']:08d}.jpg"; image.save(str(preview),'JPEG',90)
            data['preview_file'] = str(preview); self.records.append(data)
            self.gpu_forward_frames += 1; self.bounding_boxes_drawn += len(data['objects'])
            self.frames.addItem(f"第{data['frame_index']+1}帧 · PTS {data['pts']} · {len(data['objects'])}目标")
            self.frames.setCurrentRow(len(self.records)-1)
            count = len(self.records)
            self.status.setText(f"视频已读取{self.current_input['decoded']}帧；真实GPU已推理{count}帧；当前{len(data['objects'])}目标，{data['inference_ms']:.1f}ms。")
            self.read_progress(self.current_input['decoded'],self.current_input['elapsed_seconds'],self.current_input['duration'])
            self.snapshot(); self.current_input = None; self.decoder.ack.set()
        elif event == 'error':
            if 'gpu' in data: self.gpu_info = data['gpu']
            self.fail(data['message'])
        elif event == 'stopped':
            self.worker_modules = data['loaded_modules']; self.snapshot()
    @Slot(object)
    def request_prediction(self, meta):
        if self.cancel_requested:
            self.decoder.ack.set(); return
        self.current_input = meta
        self.send(dict(op='infer',threshold=self.threshold.value(), **{k:meta[k] for k in ['image','frame_index','pts','time_base','time_seconds']}))
    @Slot(int, float, float)
    def read_progress(self, decoded, seconds, duration):
        self.progress.setRange(0,1000)
        self.progress.setValue(min(999,round(seconds/duration*1000)) if duration > 0 else 0)
        self.progress.setFormat(f'视频读取进度 %p% · 已解码{decoded}帧 · 已推理{len(self.records)}帧' if duration > 0 else f'视频总时长未知 · 已解码{decoded}帧 · 已推理{len(self.records)}帧')
    def pause(self):
        if not self.decoder: return
        if self.decoder.resume.is_set():
            self.decoder.resume.clear(); self.pause_button.setText('继续'); self.status.setText('已请求暂停；正在执行的一帧完成后暂停，不增加新的推理帧。')
        else:
            self.decoder.resume.set(); self.pause_button.setText('暂停'); self.status.setText('继续真实GPU推理。')
        self.snapshot()
    def cancel(self):
        self.cancel_requested = True; self.outcome = 'CANCELLED'
        if self.decoder: self.decoder.stop()
        self.pause_button.setEnabled(False); self.cancel_button.setEnabled(False)
        self.status.setText('正在取消并停止独立Worker，释放显存…')
        if self.worker and self.worker.state() != QProcess.ProcessState.NotRunning:
            self.worker.terminate(); QTimer.singleShot(2000, self.force_stop)
        else: self.maybe_idle()
        self.snapshot()
    def force_stop(self):
        if self.worker and self.worker.state() != QProcess.ProcessState.NotRunning: self.worker.kill()
    @Slot(str)
    def fail(self, message):
        self.outcome = 'FAILED'; self.cancel_requested = True
        if self.decoder: self.decoder.stop()
        self.last_error = message
        record(self.log_dir, 'gui', 'failure', message=message)
        self.status.setText('已停止：'+message+' 诊断日志：'+str(self.log_dir)); self.snapshot()
        self.pause_button.setEnabled(False)
        if self.worker and self.worker.state() != QProcess.ProcessState.NotRunning:
            self.worker.terminate(); QTimer.singleShot(2000,self.force_stop)
        else:self.maybe_idle()
    @Slot(bool, int)
    def decode_complete(self, complete, decoded):
        if self.outcome == 'RUNNING': self.outcome = 'COMPLETE' if complete else 'CANCELLED'
        if complete and self.outcome == 'COMPLETE':
            self.progress.setValue(1000)
            self.progress.setFormat(f'视频读取进度 %p% · 已解码{decoded}帧 · 已推理{len(self.records)}帧')
            empty = not any(r['objects'] for r in self.records)
            self.status.setText(('本次未检测到超过阈值的目标。' if empty else '检测完成。') + f' 视频读取{decoded}帧，真实GPU推理{len(self.records)}帧。')
        self.send(dict(op='stop')); self.snapshot()
        self.maybe_idle()
    def worker_finished(self, code, status):
        self.read_worker(); self.log_worker()
        self.worker_exit = dict(code=code, hex=f'0x{code & 0xffffffff:08X}', status=str(status))
        record(self.log_dir, 'gui', 'worker_exit', **self.worker_exit)
        if self.decoder and self.decoder.isRunning():
            self.decoder.stop()
        if self.outcome == 'RUNNING' and not self.probing:
            self.outcome='FAILED'; self.last_error=f'Worker意外退出（{code} / 0x{code & 0xffffffff:08X}），没有CPU回退。'
            self.status.setText(self.last_error+' 诊断日志：'+str(self.log_dir))
        elif self.outcome == 'CANCELLED':self.status.setText(f'任务已取消；保留{len(self.records)}个真实已推理帧，可保存部分结果。')
        self.maybe_idle(); self.snapshot()
        if self.closing: QTimer.singleShot(100,self.close)
    @Slot()
    def maybe_idle(self):
        if self.decoder and self.decoder.isRunning(): return
        if self.worker and self.worker.state() != QProcess.ProcessState.NotRunning: return
        self.controls(False)
        if self.closing: QTimer.singleShot(100, self.close)
    def snapshot(self):
        # Diagnostics stay bounded during long videos; explicit result export retains every processed frame.
        diagnostic_frames = self.records if len(self.records) <= 100 else self.records[-20:]
        atomic_json(self.diagnostic,dict(outcome=self.outcome, gpu=self.gpu_info, model=self.model_info,
              log_dir=str(self.log_dir), worker_exit=self.worker_exit, last_error=self.last_error,
              run_config=self.run_config, diagnostic_frames_truncated=len(self.records)>100,
              inferred_frames=len(self.records), cuda_forward_frames=self.gpu_forward_frames,
              boxes_drawn=self.bounding_boxes_drawn, paused=bool(self.decoder and not self.decoder.resume.is_set()),
              worker_modules=getattr(self,'worker_modules',[]), worker_running=bool(self.worker and self.worker.state()!=QProcess.ProcessState.NotRunning),
              frames=[{k:v for k,v in r.items() if k!='preview_file'} for r in diagnostic_frames]))
    def show_frame(self, index):
        if not 0 <= index < len(self.records): return
        record = self.records[index]; self.preview = QPixmap(record['preview_file']); self.display()
        self.detail.setText(f"帧编号（从0开始）：{record['frame_index']} · 原PTS：{record['pts']} × {record['time_base']} · 原图{record['width']}×{record['height']} · {len(record['objects'])}目标 · {record['inference_ms']:.1f}ms · CUDA实际前向：{record['cuda_forward_calls']}")
    def display(self):
        if self.preview:self.picture.setPixmap(self.preview.scaled(self.picture.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'preview'):self.display()
    def save(self):
        if not self.records:return
        name, selected = QFileDialog.getSaveFileName(self,'保存本次真实检测结果','IVAD_RF_检测结果.json','JSON (*.json);;CSV (*.csv)')
        if not name:return
        if not Path(name).suffix:name += '.csv' if 'CSV' in selected else '.json'
        records=[{k:v for k,v in r.items() if k!='preview_file'} for r in self.records]
        if Path(name).suffix.lower()=='.csv':
            with open(name,'w',encoding='utf-8-sig',newline='') as f:
                writer=csv.writer(f);writer.writerow(['frame_index','pts','time_base','time_seconds','width','height','category','class_id','confidence','x1','y1','x2','y2','inference_ms','actual_inference','status'])
                for r in records:
                    for obj in r['objects'] or [None]:
                        writer.writerow([r['frame_index'],r['pts'],str(r['time_base']),r['time_seconds'],r['width'],r['height'],obj['category'] if obj else '',obj['class_id'] if obj else '',obj['confidence'] if obj else '',*(obj['xyxy'] if obj else ['']*4),r['inference_ms'],True,self.outcome])
        else:atomic_json(name,dict(status=self.outcome,model=self.model_info,gpu=self.gpu_info,**self.run_config,frames=records))
        self.status.setText('本次检测结果已保存到：'+name)
    def closeEvent(self,event):
        if self.worker and self.worker.state()!=QProcess.ProcessState.NotRunning:
            self.closing=True;self.cancel();event.ignore();return
        if self.decoder and self.decoder.isRunning():
            self.decoder.stop();self.closing=True;QTimer.singleShot(100,self.close);event.ignore();return
        if self.session and self.session.exists():shutil.rmtree(self.session)
        record(self.log_dir, 'gui', 'normal_close')
        event.accept()

def main():
    app=QApplication(sys.argv);app.setOrganizationName('IVAD');app.setApplicationName('RF Offline Demo')
    window=Window()
    def qt_log(kind, context, message):
        record(window.log_dir, 'qt', str(kind), message=message)
    qInstallMessageHandler(qt_log)
    def unhandled(kind, exc, tb):
        exception(window.log_dir, 'gui', exc)
        window.fail('界面处理异常：'+str(exc))
    sys.excepthook = unhandled
    window.show()
    code = app.exec()
    record(window.log_dir, 'gui', 'exit', code=code)
    return code

if __name__ == '__main__':raise SystemExit(main())
