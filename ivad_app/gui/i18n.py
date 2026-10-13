"""Qt翻译入口：当前提供中文，未来可安装同context的QM语言包。"""
from PySide6.QtCore import QCoreApplication

def tr(text: str) -> str:
    return QCoreApplication.translate('IVAD', text)
