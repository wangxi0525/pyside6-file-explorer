"""
run.py —— 程序入口

用法:
    python run.py                 # 从用户主目录启动
    python run.py D:\\some\\path   # 启动后直接打开指定目录
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from main_window import APP_NAME, Explorer


def enable_dpi_awareness():
    """高分屏下不糊。Qt6 默认开启，这里保留兼容处理。"""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, False)
    enable_dpi_awareness()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    win = Explorer()
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.exists(target):
            win.navigate(target)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()