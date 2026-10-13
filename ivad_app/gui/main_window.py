import json, threading
from datetime import datetime, timezone, timedelta
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QComboBox, QFrame, QStackedWidget, QSplitter, QTableWidgetItem, QApplication, QMessageBox)
from ivad_app import __version__
from ivad_app.gui.pages import (button, Dashboard, ProjectsPage, JobsPage, DevicesPage, LogsPage, SettingsPage, Placeholder)
from ivad_app.gui.async_runner import AsyncRunner
from ivad_app.gui.style import STYLE
from ivad_app.services.logging_service import redact
from ivad_app.gui.i18n import tr

def local_time(value):
    return datetime.fromisoformat(value).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')

DEV = [('总览', 'dashboard'), ('项目管理', 'projects'), ('视频管理', 'media'), ('标注工作台', 'annotation'),
       ('数据集管理', 'dataset'), ('AI训练', 'training'), ('模型仓库', 'models'), ('系统设置', 'settings')]
PRODUCTION = [('监控总览', 'monitoring'), ('摄像头管理', 'cameras'), ('视频检测', 'detection'),
              ('报警中心', 'alarms'), ('事件复核', 'review'), ('系统状态', 'devices')]

def fill_table(table, rows):
    selected = table.item(table.currentRow(), 0).text() if table.currentRow() >= 0 and table.item(table.currentRow(), 0) else None
    table.blockSignals(True)
    table.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value)); item.setToolTip(str(value)); table.setItem(row, column, item)
        if selected and values[0] == selected: table.selectRow(row)
    table.blockSignals(False)

class MainWindow(QMainWindow):
    shutdown_done = Signal(str)
    def __init__(self, services, *, auto_probe=True):
        super().__init__()
        self.s = services
        self.project_busy = self.refresh_busy = self.probe_busy = False
        self.log_filter = None
        self.is_closing = self.may_close = False
        self.runner = AsyncRunner(self.s.logs, self)
        self.runner.error.connect(self.show_error)
        self.shutdown_done.connect(self.finish_shutdown)
        self.setWindowTitle(f'IVAD Platform {__version__} · 工业视觉异常检测')
        available = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1440, available.width() - 30), min(900, available.height() - 65))
        self.setMinimumSize(1040, 660); self.setStyleSheet(STYLE)
        outer = QWidget(); self.setCentralWidget(outer)
        layout = QVBoxLayout(outer); layout.setContentsMargins(16, 14, 16, 12)
        header = QHBoxLayout()
        brand = QLabel('IVAD Platform'); brand.setObjectName('brand'); header.addWidget(brand)
        header.addWidget(QLabel(f'{__version__}  /  应用基础')); header.addStretch()
        self.project_label = QLabel('当前项目：未打开'); self.project_label.setMinimumWidth(200); self.project_label.setMaximumWidth(280)
        header.addWidget(self.project_label)
        self.workspace = QComboBox(); self.workspace.setObjectName('workspace_mode')
        self.workspace.addItems([tr('开发模式'), tr('生产监控模式')]); self.workspace.currentIndexChanged.connect(self.switch_workspace)
        header.addWidget(self.workspace); layout.addLayout(header)
        self.notice = QLabel('P1 · GPU检查尚未执行。后续功能显示 Not Implemented。')
        self.notice.setObjectName('notice'); self.notice.setWordWrap(True); layout.addWidget(self.notice)
        splitter = QSplitter(); layout.addWidget(splitter, 1)
        sidebar = QFrame(); sidebar.setObjectName('sidebar'); sidebar.setMinimumWidth(180); sidebar.setMaximumWidth(260)
        side = QVBoxLayout(sidebar); side.addWidget(QLabel('工作空间'))
        self.nav = QListWidget(); self.nav.setMinimumWidth(170); self.nav.setObjectName('navigation'); self.nav.currentRowChanged.connect(self.navigate); side.addWidget(self.nav, 1)
        for title, key in [('任务中心', 'jobs'), ('设备与后端', 'devices'), ('诊断日志', 'logs')]:
            side.addWidget(button(title, lambda _=False, key=key: self.show_page(key)))
        side.addWidget(QLabel('仅 P1\n本地运行 · 不启动网络服务'))
        splitter.addWidget(sidebar)
        self.stack = QStackedWidget(); self.stack.setMinimumWidth(610); splitter.addWidget(self.stack)
        self.pages = {'dashboard': Dashboard(), 'projects': ProjectsPage(), 'jobs': JobsPage(), 'devices': DevicesPage(), 'logs': LogsPage(), 'settings': SettingsPage()}
        placeholders = {
            'media': ('视频管理', 'P2', '视频复制/引用、固定/变化抽帧与来源追溯。'),
            'annotation': ('标注工作台', 'P2', '框、Mask、ROI、整帧和片段标签，人工审核与保存。'),
            'dataset': ('数据集管理', 'P2', '不可变数据快照、分组划分与导出。'),
            'training': ('AI训练', 'P3', 'GPU-only训练、验证和检查点管理。'),
            'models': ('模型仓库', 'P3', '实验→候选→生产，人工批准发布和回滚。'),
            'monitoring': ('监控总览', 'P4', '离线录像检测进度与报警事件；当前没有生产检测数据。'),
            'cameras': ('摄像头管理', 'P4；RTSP未来阶段', '管理录像来源的摄像头关联，RTSP接入尚未实现。'),
            'detection': ('视频检测', 'P4', '新录像GPU检测与时间轴回放。'),
            'alarms': ('报警中心', 'P4', '规则计算、报警记录、原图与片段证据。'),
            'review': ('事件复核', 'P4–P5', '人工复核与候选标注回流，训练由用户触发。'),
        }
        for key, args in placeholders.items(): self.pages[key] = Placeholder(*args)
        for page in self.pages.values(): self.stack.addWidget(page)
        right = QFrame(); right.setObjectName('card'); right.setMinimumWidth(170); right.setMaximumWidth(260)
        props = QVBoxLayout(right); props.addWidget(QLabel('当前上下文'))
        self.properties = QLabel('未打开项目\n\n后端：尚未检查'); self.properties.setWordWrap(True); self.properties.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        props.addWidget(self.properties); props.addStretch(); props.addWidget(QLabel('阶段：P1\n运行模式：本地\nIntel：未验证'))
        splitter.addWidget(right); splitter.setSizes([220, 980, 200]); splitter.setChildrenCollapsible(False)
        self.global_tasks = QLabel('任务队列：读取中'); self.statusBar().addPermanentWidget(self.global_tasks)
        self.statusBar().showMessage('就绪 · P1')
        p = self.pages['projects']
        p.create_requested.connect(self.create_project); p.open_requested.connect(self.open_project)
        p.save_requested.connect(self.save_project); p.close_requested.connect(self.close_project); p.check_requested.connect(self.check_project)
        j = self.pages['jobs']
        j.submit_requested.connect(self.submit_job); j.cancel_requested.connect(lambda job: self.runner.run(lambda: self.s.jobs.cancel(job)))
        j.logs_requested.connect(self.show_job_logs)
        self.pages['devices'].refresh_requested.connect(self.probe_devices)
        self.pages['settings'].save_requested.connect(self.save_settings)
        self.pages['logs'].copy_requested.connect(self.copy_diagnostics)
        self.pages['logs'].clear_filter_requested.connect(lambda: self.show_job_logs(None))
        self.timer = QTimer(self); self.timer.setInterval(600); self.timer.timeout.connect(self.refresh); self.timer.start()
        self.switch_workspace(0); self.load_settings(); self.refresh()
        if auto_probe: QTimer.singleShot(100, self.probe_devices)

    def show_error(self, message):
        self.notice.setObjectName('error'); self.notice.setStyleSheet('background:#fff0ed;color:#943b2f;padding:10px;border-radius:6px;')
        self.notice.setText(message); self.statusBar().showMessage(message)

    def show_notice(self, message):
        self.notice.setStyleSheet(''); self.notice.setObjectName('notice')
        self.notice.style().unpolish(self.notice); self.notice.style().polish(self.notice)
        self.notice.setText(message); self.statusBar().showMessage(message, 7000)

    def switch_workspace(self, mode):
        self.nav.blockSignals(True); self.nav.clear()
        self.navigation = DEV if mode == 0 else PRODUCTION
        for title, _ in self.navigation: self.nav.addItem(tr(title))
        self.nav.blockSignals(False); self.nav.setCurrentRow(0)
        self.s.logs.write('gui', '切换工作空间：' + ('开发模式' if mode == 0 else '生产监控模式'))

    def navigate(self, row):
        if 0 <= row < len(self.navigation): self.show_page(self.navigation[row][1])

    def show_page(self, key):
        self.nav.blockSignals(True)
        self.nav.setCurrentRow(next((i for i, (_, value) in enumerate(self.navigation) if value == key), -1))
        self.nav.blockSignals(False)
        self.stack.setCurrentWidget(self.pages[key])
        self.s.logs.write('gui', '打开页面：' + key)

    def project_operation(self, operation, message):
        if self.project_busy: return
        self.project_busy = True; self.pages['projects'].refresh_controls(True)
        def done(result, error):
            self.project_busy = False
            if not error: self.pages['projects'].set_project(self.s.projects.current)
            else: self.pages['projects'].refresh_controls()
            self.update_project_summary()
            if not error: self.show_notice(message)
            self.refresh()
        self.runner.run(operation, done)

    def create_project(self, parent, name, description, site):
        self.project_operation(lambda: self.s.projects.create(parent, name, description, site), '项目已创建并打开。')

    def open_project(self, root):
        if not self.confirm_discard(): return
        self.project_operation(lambda: self.s.projects.open(root), '项目已打开。')

    def save_project(self, name, description, site, revision):
        self.project_operation(lambda: self.s.projects.save(name, description, site, revision), '项目配置已保存。')

    def close_project(self):
        if not self.confirm_discard(): return
        self.project_operation(self.s.projects.close, '当前项目已关闭，文件保留。')

    def confirm_discard(self):
        current = self.s.projects.current; page = self.pages['projects']
        if current and (page.name.text(), page.description.toPlainText(), page.site.text()) != (current.name, current.description, current.site):
            answer = QMessageBox.question(self, '未保存的项目修改', '当前项目有未保存的修改。是否放弃修改？选择取消后可点击“保存配置”。', QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            return answer == QMessageBox.StandardButton.Discard
        return True

    def check_project(self):
        self.project_operation(self.s.projects.check, '项目目录UUID、数据库Schema和完整性检查通过。')

    def update_project_summary(self):
        p = self.s.projects.current
        name = p.name if p else '未打开'
        self.project_label.setText(self.project_label.fontMetrics().elidedText('当前项目：' + name, Qt.TextElideMode.ElideRight, 270))
        self.project_label.setToolTip(name)
        self.setWindowTitle(f'IVAD Platform {__version__}' + (f' · {p.name}' if p else ''))
        self.pages['dashboard'].summary.setText(f'项目：{p.name}\nUUID：{p.id}\nSchema：{p.schema} · 修订：{p.revision}' if p else '尚未打开项目；请在项目管理中创建或打开。')
        self.update_properties()

    def update_properties(self):
        p = self.s.projects.current
        devices = self.s.devices.snapshot()
        self.properties.setText((f'项目：{p.name}\n修订：{p.revision}' if p else '未打开项目') + '\n\n' + '\n'.join(d.name + '\n' + d.status for d in devices or []))

    def submit_job(self, kind):
        project = self.s.projects.current
        self.runner.run(lambda: self.s.jobs.submit(kind, project.id if project else None), lambda _, error: self.show_notice('非AI任务已提交。') if not error else None)

    def show_job_logs(self, job_id):
        self.log_filter = job_id; self.pages['logs'].filter_label.setText('任务UUID：' + job_id if job_id else '显示最近150条日志')
        self.show_page('logs'); self.refresh()

    def probe_devices(self):
        if self.probe_busy: return
        self.probe_busy = True; self.pages['devices'].refresh_button.setEnabled(False)
        self.show_notice('正在后台检查GPU环境；界面可继续操作。')
        def done(devices, error):
            self.probe_busy = False; self.pages['devices'].refresh_button.setEnabled(True)
            if error: return
            self.pages['devices'].counts.setText(f"NVIDIA GPU：{sum(d.id.startswith('nvidia:') and d.hardware_detected for d in devices)} · CUDA可用：{sum(d.id.startswith('nvidia:') and d.backend_available for d in devices)} · 匹配实测验证：{sum(d.backend_validated for d in devices)}")
            fill_table(self.pages['devices'].devices, [[d.name, d.backend, '是' if d.hardware_detected else '否/未知', '是' if d.backend_available else '否', '是（P0匹配证据）' if d.backend_validated else 'Not Tested', d.status] for d in devices])
            descriptions = []
            for d in devices:
                details = d.details
                lines = [f'设备：{d.name}', f'后端：{d.backend}', f'状态：{d.status}']
                if 'driver' in details: lines.append(f"驱动：{details['driver']} · 总显存：{details['total_mib']} MiB · 可用：{details['free_mib']} MiB · 已用：{details['used_mib']} MiB")
                if 'torch' in details: lines.append(f"PyTorch：{details['torch']} · CUDA：{details['cuda']} · ORT：{details['ort']}\nCUDA张量实测：{'通过' if details['cuda_tensor_verified'] else '未通过'} · 当前GPU使用率：{details['utilization_percent']}%")
                lines.append('验证依据：' + details.get('evidence', '未验证'))
                if details.get('error'): lines.append('错误：' + details['error'])
                descriptions.append('\n'.join(lines))
            self.pages['devices'].details.setPlainText('\n\n'.join(descriptions))
            self.load_device_choices(devices); self.update_properties()
            self.show_notice('设备检查完成。' if all(d.status != 'Error' for d in devices) else '设备检查存在错误；AI后端不可用，请查看设备信息。')
        self.runner.run(self.s.devices.probe, done)

    def load_device_choices(self, devices):
        combo = self.pages['settings'].preferred
        selected = combo.currentData(); combo.clear(); combo.addItem('自动选择已检测NVIDIA GPU', '')
        for device in devices:
            if device.backend_available: combo.addItem(device.name + ' · ' + device.id, device.id)
        index = combo.findData(selected)
        if selected and index < 0:
            combo.addItem('已保存设备（当前不可用）', selected); index = combo.findData(selected)
        combo.setCurrentIndex(max(0, index))

    def load_settings(self):
        def done(prefs, error):
            if error: return
            page = self.pages['settings']; page.worker.setText(prefs.get('worker_python', ''))
            saved = prefs.get('preferred_gpu', '')
            if saved and page.preferred.findData(saved) < 0: page.preferred.addItem('已保存设备（待检查）', saved)
            page.preferred.setCurrentIndex(max(0, page.preferred.findData(saved)))
        self.runner.run(self.s.settings.preferences, done)

    def save_settings(self, prefs):
        def done(_, error):
            if not error:
                self.show_notice('设置已保存；GPU状态将重新检查。'); self.probe_devices()
        self.runner.run(lambda: self.s.settings.save_preferences(prefs), done)

    def refresh(self):
        if self.refresh_busy or self.is_closing: return
        self.refresh_busy = True
        log_filter = self.log_filter
        def collect():
            return self.s.jobs.history(), self.s.logs.recent(log_filter), self.s.settings.recent_projects()
        def done(result, error):
            self.refresh_busy = False
            if error: return
            jobs, logs, recent = result
            fill_table(self.pages['jobs'].jobs, [[j['id'], '非AI诊断' if j['kind'] == 'diagnostic' else '可控异常测试', j['state'], str(j['progress']) + '%', local_time(j['updated_at']), j['error']] for j in jobs])
            self.pages['jobs'].show_detail()
            self.global_tasks.setText(f"任务：运行{sum(j['state']=='RUNNING' for j in jobs)} / 排队{sum(j['state']=='QUEUED' for j in jobs)} / 历史{len(jobs)}")
            if log_filter == self.log_filter:
                self.pages['logs'].rows = logs
                fill_table(self.pages['logs'].logs, [[local_time(row['timestamp']), row['level'], row['category'], row['message']] for row in logs])
            fill_table(self.pages['projects'].recent, [[p['name'], p['id'], p['root']] for p in recent])
        self.runner.run(collect, done)

    def copy_diagnostics(self):
        text = f'IVAD {__version__}\nAPI v1 / SQLite\n' + self.global_tasks.text() + '\n'
        text += '\n'.join(d.name + ' / ' + d.status for d in self.s.devices.snapshot()) + '\n'
        text += json.dumps(self.pages['logs'].rows, ensure_ascii=False, indent=2)
        QApplication.clipboard().setText(redact(text)); self.show_notice('诊断摘要与技术日志已复制，路径与凭据已脱敏。')

    def closeEvent(self, event):
        if self.may_close: event.accept(); return
        event.ignore()
        if self.is_closing: return
        if not self.confirm_discard(): return
        self.is_closing = True; self.timer.stop(); self.s.jobs.request_shutdown()
        self.show_notice('正在安全关闭：取消诊断任务，等待后台检查并关闭数据库…')
        self.centralWidget().setEnabled(False)
        def shutdown():
            try:
                self.runner.stop(); self.s.close(); self.shutdown_done.emit('')
            except Exception:
                self.shutdown_done.emit('后台关闭失败，请查看技术日志。')
        threading.Thread(target=shutdown, name='IVAD-Shutdown', daemon=False).start()

    @Slot(str)
    def finish_shutdown(self, error):
        if error:
            self.show_error(error); return
        self.may_close = True; self.close()
