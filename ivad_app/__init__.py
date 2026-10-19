"""IVAD：当前只交付P1应用基础。"""
import sys
from pathlib import Path
__version__ = '1.0.0-P2-Beta.2' if getattr(sys, 'frozen', False) else '1.0.0-P3-Dev.2'
if getattr(sys, 'frozen', False) and (Path(sys._MEIPASS)/'p37d-lite-profile.json').is_file():
    __version__ = '1.0.0-P37D-Lite-Candidate'
