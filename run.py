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

# 兜底隐藏控制台：从源码用 python.exe 启动时（而非 pythonw.exe），
# Windows 会附带一个控制台窗口。这里用 FreeConsole 把它摘掉，
# 打包 exe 时本就不会有控制台，这段只在源码运行时起作用。
if os.name == "nt" and not getattr(sys, "frozen", False):
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # 先判断自己是否独占控制台，独占才摘，避免影响父进程
        if kernel32.GetConsoleProcessList(None, 0) == 1:
            kernel32.FreeConsole()
    except Exception:
        pass

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


def acquire_single_instance():
    """
    单实例保护：同一时间只允许一个主窗口。

    用命名互斥体实现。若已有实例，则激活它并退出，
    避免出现多个窗口同时被误触发出现在任务栏。
    """
    if sys.platform != "win32":
        return None

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    # 名字里带上当前用户的会话 id，避免不同用户互相影响
    sid = wintypes.DWORD()
    kernel32.ProcessIdToSessionId(kernel32.GetCurrentProcessId(),
                                 ctypes.byref(sid))
    name = f"Local\\QtExplorer_{APP_NAME}_{sid.value}".replace(" ", "_")

    handle = kernel32.CreateMutexW(None, True, name)
    if not handle:
        return None          # 拿不到互斥体就不拦，让程序照常跑

    already = kernel32.GetLastError() == 183   # ERROR_ALREADY_EXISTS
    if already:
        # 找已有窗口并激活它
        WNDENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        found = []

        def cb(hwnd, _):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if APP_NAME in buf.value and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(cb), 0)
        for hwnd in found:
            user32.ShowWindow(hwnd, 9)          # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
        kernel32.CloseHandle(handle)
        return False

    return handle            # 首个实例，句柄要留着直到进程结束


def main():
    enable_dpi_awareness()

    mutex = acquire_single_instance()
    if mutex is False:
        return              # 已有实例在运行，已激活它，本进程退出

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