from pathlib import Path
from PySide6.QtCore import QDir
QDir.addSearchPath('ivad_icons',str(Path(__file__).parent/'icons'))
STYLE = '''
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; color: #203047; }
QMainWindow { background: #f2f5fa; }
QDialog, QMessageBox { background: #f2f5fa; color: #203047; }
QWidget#p3Training, QWidget#p3Models, QWidget#p3TrainingBody, QScrollArea#p3TrainingScroll { background: #f2f5fa; color: #203047; }
QFrame#sidebar { background: #13243a; border-radius: 10px; }
QFrame#sidebar QLabel { color: #dce6f5; }
QListWidget#navigation { background: transparent; color: #dce6f5; border: none; outline: none; }
QListWidget#navigation::item { padding: 12px 10px; border-radius: 6px; margin: 2px 0; }
QListWidget#navigation::item:selected { background: #254467; color: white; }
QLabel#title { font-size: 24px; font-weight: 600; }
QLabel#brand { font-size: 22px; font-weight: 600; }
QLabel#subtitle { color: #65788f; }
QFrame#card { background: white; border: 1px solid #dde4ee; border-radius: 10px; }
QPushButton { background: white; border: 1px solid #c9d4e2; padding: 8px 14px; border-radius: 6px; }
QPushButton:hover { background: #e9f1ff; border-color: #6690c5; }
QPushButton:disabled { color: #a1adbc; background: #f0f3f7; }
QPushButton#primary { background: #2563a8; color: white; border: none; }
QPushButton#primary:hover { background: #1d508c; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox { background: white; border: 1px solid #cbd6e4; border-radius: 5px; padding: 7px; }
QComboBox { color: #203047; padding-right: 24px; }
QComboBox:hover, QComboBox:focus { border-color: #6690c5; }
QComboBox:disabled { background: #f0f3f7; color: #738092; border-color: #d8e0e9; }
QComboBox QAbstractItemView { background: #ffffff; color: #203047; border: 1px solid #8a9bb0; selection-background-color: #d6e8ff; selection-color: #203047; outline: none; }
QComboBox QAbstractItemView::item { min-height: 26px; padding: 4px 8px; background: #ffffff; color: #203047; }
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected { background: #d6e8ff; color: #203047; }
QComboBox QAbstractItemView::item:disabled { background: #f0f3f7; color: #738092; }
QSpinBox, QDoubleSpinBox { background: white; color: #203047; border: 1px solid #cbd6e4; border-radius: 5px; padding: 5px; min-height: 22px; }
QCheckBox::indicator { background: white; border: 1px solid #8a9bb0; width: 16px; height: 16px; }
QCheckBox::indicator:checked { background: #2563a8; }
QTableWidget::indicator { background: white; border: 1px solid #8a9bb0; width: 16px; height: 16px; }
QTableWidget::indicator:checked { background: #2563a8; }
QTableWidget { background: white; border: 1px solid #dde4ee; gridline-color: #edf1f6; }
QListWidget { background: white; border: 1px solid #dde4ee; }
QListWidget::item:selected { background: #d6e8ff; color: #203047; }
QListWidget#annotation_frames::item { min-height:28px; padding:3px 1px; }
QListWidget::indicator, QCheckBox::indicator, QTableWidget::indicator { width:20px; height:20px; border:2px solid #3c5575; background:#ffffff; border-radius:3px; }
QListWidget::indicator:hover, QCheckBox::indicator:hover, QTableWidget::indicator:hover { border:2px solid #155a9e; background:#e4f0ff; }
QListWidget::indicator:checked, QCheckBox::indicator:checked, QTableWidget::indicator:checked { image:url(ivad_icons:checked.svg); border:2px solid #16538e; background:#2166aa; }
QListWidget::indicator:disabled, QCheckBox::indicator:disabled, QTableWidget::indicator:disabled { border:2px solid #8d9aaa; background:#e7ebf0; }
QListWidget::indicator:checked:disabled, QCheckBox::indicator:checked:disabled, QTableWidget::indicator:checked:disabled { image:url(ivad_icons:checked.svg); background:#8396aa; }
QHeaderView::section { background: #eaf0f7; border: none; padding: 8px; font-weight: 600; }
QLabel#notice { background: #e7effb; color: #234f84; padding: 10px; border-radius: 6px; }
QLabel#error { background: #fff0ed; color: #943b2f; padding: 10px; border-radius: 6px; }
QProgressBar { border: 1px solid #d8e2ef; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: #4687bf; }

QWidget#project_management_page, QWidget#project_tab_body, QWidget#camera_tab_body, QWidget#camera_management_panel { background: #f2f5fa; color: #203047; }
QTabWidget#project_camera_tabs::pane { background: #f2f5fa; border: 1px solid #cbd6e4; }
QTabWidget#project_camera_tabs QTabBar::tab { background: #2479a2; color: white; padding: 10px 22px; border: 1px solid #cbd6e4; }
QTabWidget#project_camera_tabs QTabBar::tab:selected, QTabWidget#project_camera_tabs QTabBar::tab:hover { background: white; color: #203047; }
QWidget#project_management_page QPushButton:disabled { background: #e7ebf0; color: #65758a; }
QWidget#camera_management_panel QLabel:disabled, QWidget#camera_management_panel QCheckBox:disabled { color: #65758a; }
QWidget#camera_management_panel QLineEdit:disabled { background: #f0f3f7; color: #65758a; }
QWidget#project_management_page QAbstractItemView { background: white; alternate-background-color: #f0f5fb; color: #203047; selection-background-color: #d6e8ff; selection-color: #203047; }
'''
