"""
run.py —— 程序入口

用法:
    python run.py# 从用户主目录启动
    python run.py D:\\some\\path   # 启动后直接打开指定目录

同时也是 PyInstaller 打包的入口脚本。
"""
import os
import sys

# 打包成 exe 后 __file__ 指向解包目录，源码目录需要单独处理
if getattr(sys, "frozen", False):
    APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from main_window import APP_NAME, Explorer

ICON_NAME = "app_icon.ico"


def resource_path(*parts) -> str:
    """定位随包携带的资源，兼容源码运行与打包两种情况。"""
    return os.path.join(APP_DIR, *parts)


def enable_dpi_awareness():
    """高分屏下不糊。Qt6 默认开启，这里保留兼容处理。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


def main():
    enable_dpi_awareness()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("QtExplorer")
    app.setFont(QFont("Microsoft YaHei UI", 9))

    icon_file = resource_path(ICON_NAME)
    app_icon = QIcon(icon_file) if os.path.isfile(icon_file) else QIcon()
    app.setWindowIcon(app_icon)

    win = Explorer()
    win.setWindowIcon(app_icon)

    # 支持"拖到 exe 图标上打开"：命令行给的是目录
    for arg in sys.argv[1:]:
        if os.path.exists(arg):
            win.navigate(arg)
            break

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()