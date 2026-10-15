"""P1基础页面；后续功能有清晰阶段说明，未提供假动作按钮。"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFormLayout,
    QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget, QHeaderView, QComboBox, QFileDialog, QFrame, QScrollArea, QTabWidget)
from ivad_app.gui.i18n import tr

def button(text, handler, primary=False, name=''):
    widget = QPushButton(tr(text))
    widget.setObjectName(name or ('primary' if primary else ''))
    widget.clicked.connect(lambda checked=False: handler())
    return widget

def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    widget.verticalHeader().hide()
    widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    widget.setAlternatingRowColors(True)
    widget.setWordWrap(False)
    return widget

class Page(QWidget):
    def __init__(self, title, description):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(22, 20, 22, 20); self.layout.setSpacing(14)
        label = QLabel(tr(title)); label.setObjectName('title'); self.layout.addWidget(label)
        subtitle = QLabel(tr(description)); subtitle.setObjectName('subtitle'); subtitle.setWordWrap(True)
        self.layout.addWidget(subtitle)

class Placeholder(Page):
    def __init__(self, title, phase, description):
        super().__init__(title, description)
        self.status = QLabel(f'Not Implemented · 尚未实现\n计划阶段：{phase}')
        self.status.setObjectName('notice'); self.status.setWordWrap(True)
        self.layout.addWidget(self.status)
        self.layout.addWidget(QLabel('此页仅保留统一导航。当前不会执行视频、标注、训练、推理或报警操作。'))
        self.layout.addStretch()

class Dashboard(Page):
    def __init__(self):
        super().__init__('应用总览', 'P2 · 视频、人工标注与数据集管理已接入。生产检测与报警尚未实现。')
        self.summary = QLabel('尚未打开项目'); self.summary.setWordWrap(True); self.summary.setObjectName('notice')
        self.layout.addWidget(self.summary)
        available=QLabel('可用功能：项目、视频导入与播放、PTS抽帧、人工框/多边形/ROI标注、类别管理、数据集冻结与导出、任务与诊断。');available.setWordWrap(True);self.layout.addWidget(available)
        self.layout.addWidget(QLabel('默认模型候选：YOLO26n（NVIDIA P0实测）\nIntel后端：Not Tested；独立历史P0 BLOCKED。'))
        self.layout.addStretch()

class ProjectsPage(Page):
    create_requested = Signal(str, str, str, str)
    open_requested = Signal(str)
    save_requested = Signal(str, str, str, int)
    close_requested = Signal()
    check_requested = Signal()

    def __init__(self):
        super().__init__('项目管理', '新建选煤厂项目，或打开已有项目目录。在此编辑并保存名称、厂区和描述。')
        self.setObjectName('project_management_page')
        self.tabs = QTabWidget(); self.tabs.setObjectName('project_camera_tabs')
        self.layout.addWidget(self.tabs, 1)
        self.project_body = QWidget(); self.project_body.setObjectName('project_tab_body')
        self.project_body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content = QVBoxLayout(self.project_body)
        self.project_scroll = QScrollArea(); self.project_scroll.setWidgetResizable(True)
        self.project_scroll.setWidget(self.project_body)
        self.tabs.addTab(self.project_scroll, '项目管理')
        self.camera_body = QWidget(); self.camera_body.setObjectName('camera_tab_body')
        self.camera_body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.camera_layout = QVBoxLayout(self.camera_body)
        self.camera_scroll = QScrollArea(); self.camera_scroll.setWidgetResizable(True)
        self.camera_scroll.setWidget(self.camera_body)
        self.tabs.addTab(self.camera_scroll, '摄像头管理')
        self.tabs.setCurrentIndex(0)
        content.addWidget(button('进入摄像头管理', lambda: self.tabs.setCurrentIndex(1), name='project_camera_details'))
        self.revision = 0; self.loaded = False
        self.name = QLineEdit(); self.name.setObjectName('project_name'); self.name.setPlaceholderText('例如：一号选煤厂')
        self.site = QLineEdit(); self.site.setObjectName('project_site'); self.site.setPlaceholderText('厂区或设备关联信息（可选）')
        self.description = QTextEdit(); self.description.setObjectName('project_description'); self.description.setMaximumHeight(110)
        form = QFormLayout(); form.addRow('项目名称', self.name); form.addRow('厂区信息', self.site); form.addRow('项目描述', self.description)
        content.addLayout(form)
        row = QHBoxLayout()
        self.create_button = button('新建项目…', self.choose_create, True, 'create_project')
        self.open_button = button('打开项目…', self.choose_open, name='open_project')
        self.save_button = button('保存配置', self.save, name='save_project')
        self.close_button = button('关闭项目', self.close_requested.emit, name='close_project')
        self.check_button = button('一致性检查', self.check_requested.emit, name='check_project')
        for item in [self.create_button, self.open_button, self.save_button, self.close_button, self.check_button]: row.addWidget(item)
        content.addLayout(row)
        self.info = QLabel('尚未打开项目 · 新建项目请选择存储父目录'); self.info.setWordWrap(True); self.info.setObjectName('notice')
        content.addWidget(self.info)
        content.addWidget(QLabel('最近打开的项目（双击打开；路径失效时会显示错误，不会删除项目）'))
        self.recent = table(['名称', 'UUID', '位置']); self.recent.setObjectName('recent_projects')
        self.recent.cellDoubleClicked.connect(self.open_recent); content.addWidget(self.recent, 1)
        self.refresh_controls()

    def choose_create(self):
        if not self.name.text().strip():
            self.create_requested.emit('', '', '', ''); return
        path = QFileDialog.getExistingDirectory(self, '选择项目存储父目录')
        if path: self.create_requested.emit(path, self.name.text(), self.description.toPlainText(), self.site.text())

    def choose_open(self):
        path = QFileDialog.getExistingDirectory(self, '选择含project.json的项目目录')
        if path: self.open_requested.emit(path)

    def open_recent(self, row, _):
        item = self.recent.item(row, 2)
        if item: self.open_requested.emit(item.text())

    def save(self):
        self.save_requested.emit(self.name.text(), self.description.toPlainText(), self.site.text(), self.revision)

    def set_project(self, project):
        self.loaded = project is not None
        self.revision = project.revision if project else 0
        self.name.setText(project.name if project else '')
        self.description.setPlainText(project.description if project else '')
        self.site.setText(project.site if project else '')
        self.info.setText(f'UUID：{project.id}\n目录：{project.root}\nSchema：{project.schema} · 配置修订：{project.revision}' if project else '尚未打开项目 · 新建项目请选择存储父目录')
        self.refresh_controls()

    def refresh_controls(self, busy=False):
        for item in [self.create_button, self.open_button, self.recent]: item.setEnabled(not busy)
        for item in [self.save_button, self.close_button, self.check_button]: item.setEnabled(self.loaded and not busy)

class JobsPage(Page):
    submit_requested = Signal(str)
    cancel_requested = Signal(str)
    logs_requested = Signal(str)

    def __init__(self):
        super().__init__('任务中心', '持久化串行队列。以下诊断任务只验证基础设施，不执行AI。')
        row = QHBoxLayout()
        self.submit_button = button('提交非AI诊断任务', lambda: self.submit_requested.emit('diagnostic'), True, 'submit_job')
        self.fail_button = button('测试异常处理', lambda: self.submit_requested.emit('diagnostic_failure'), name='fail_job')
        self.cancel_button = button('取消选中任务', self.cancel_selected, name='cancel_job')
        self.log_button = button('查看任务日志', self.show_logs)
        for item in [self.submit_button, self.fail_button, self.cancel_button, self.log_button]: row.addWidget(item)
        self.layout.addLayout(row)
        self.jobs = table(['任务UUID', '类型', '状态', '进度', '时间', '错误']); self.jobs.setObjectName('jobs_table')
        self.layout.addWidget(self.jobs, 1)
        self.detail = QPlainTextEdit(); self.detail.setReadOnly(True); self.detail.setMaximumHeight(120)
        self.layout.addWidget(self.detail)
        self.jobs.itemSelectionChanged.connect(self.show_detail)
        self.show_detail()

    def selected_id(self):
        row = self.jobs.currentRow()
        return self.jobs.item(row, 0).text() if row >= 0 and self.jobs.item(row, 0) else ''

    def cancel_selected(self):
        if self.selected_id(): self.cancel_requested.emit(self.selected_id())

    def show_logs(self):
        if self.selected_id(): self.logs_requested.emit(self.selected_id())

    def show_detail(self):
        row = self.jobs.currentRow()
        self.detail.setPlainText('\n'.join(self.jobs.item(row, col).text() for col in range(6)) if row >= 0 and self.jobs.item(row, 5) else '')
        selected = bool(self.selected_id())
        self.log_button.setEnabled(selected)
        state = self.jobs.item(row, 2).text() if selected and self.jobs.item(row, 2) else ''
        self.cancel_button.setEnabled(state in {'QUEUED', 'RUNNING'})

class DevicesPage(Page):
    refresh_requested = Signal()
    def __init__(self):
        super().__init__('设备与后端状态', '硬件检测、后端可用、实际验证分别记录。不会自动降级至CPU。')
        self.refresh_button = button('检查设备与GPU环境', self.refresh_requested.emit, True, 'probe_gpu')
        self.layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.counts = QLabel('GPU数量与后端状态：尚未检查'); self.layout.addWidget(self.counts)
        self.devices = table(['GPU', '后端', '硬件检测', '后端可用', '实测验证', '状态']); self.devices.setObjectName('devices_table')
        self.layout.addWidget(self.devices, 1)
        self.details = QPlainTextEdit(); self.details.setReadOnly(True); self.details.setMaximumHeight(220)
        self.layout.addWidget(self.details)
        self.layout.addWidget(QLabel('验证状态引用匹配软硬件的P0历史证据；当前检查不重新执行YOLO训练/推理。'))

class LogsPage(Page):
    copy_requested = Signal()
    export_requested = Signal()
    clear_filter_requested = Signal()
    def __init__(self):
        super().__init__('诊断日志', '应用、项目、任务、设备与数据库日志。诊断文本已作路径与凭据脱敏。')
        row = QHBoxLayout(); row.addWidget(button('复制诊断信息', self.copy_requested.emit, True, 'copy_diagnostics'))
        row.addWidget(button('导出诊断ZIP…', self.export_requested.emit, name='export_diagnostics'))
        row.addWidget(button('显示全部日志', self.clear_filter_requested.emit)); row.addStretch(); self.layout.addLayout(row)
        self.filter_label = QLabel('显示最近150条日志'); self.layout.addWidget(self.filter_label)
        self.logs = table(['时间', '级别', '类别', '摘要']); self.layout.addWidget(self.logs, 1)
        self.detail = QPlainTextEdit(); self.detail.setReadOnly(True); self.layout.addWidget(self.detail, 1)
        self.rows = []; self.logs.itemSelectionChanged.connect(self.select_detail)

    def select_detail(self):
        row = self.logs.currentRow()
        if 0 <= row < len(self.rows):
            data = self.rows[row]
            self.detail.setPlainText(data['message'] + '\n' + data['trace'])

class SettingsPage(Page):
    save_requested = Signal(dict)
    def __init__(self):
        super().__init__('系统设置', '管理独立NVIDIA Worker环境和设备选择。不会修改系统Python或CUDA。')
        self.language = QComboBox(); self.language.addItem('简体中文', 'zh_CN')
        self.worker = QLineEdit(); self.worker.setObjectName('worker_python'); self.worker.setPlaceholderText('默认使用项目 .venv-nvidia/Scripts/python.exe')
        row = QHBoxLayout(); row.addWidget(self.worker); row.addWidget(button('选择解释器…', self.choose_worker))
        self.preferred = QComboBox(); self.preferred.addItem('自动选择已检测NVIDIA GPU', '')
        form = QFormLayout(); form.addRow('界面语言', self.language); form.addRow('GPU Worker', row); form.addRow('首选设备', self.preferred)
        self.layout.addLayout(form)
        self.layout.addWidget(button('保存设置', self.save, True, 'save_settings'), alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(QLabel('Intel XPU / OpenVINO：独立Worker接口已预留，当前未实现，历史验证BLOCKED。\nAPI契约v1已预留；本阶段不启动网络服务。'))
        self.layout.addStretch()

    def choose_worker(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择可信NVIDIA环境python.exe', '', 'Python解释器 (python.exe)')
        if path: self.worker.setText(path)

    def save(self):
        self.save_requested.emit({'language': self.language.currentData(), 'worker_python': self.worker.text().strip(), 'preferred_gpu': self.preferred.currentData()})
