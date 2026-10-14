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

# ---------------------------------------------------------------------------
# 抑制启动瞬间的控制台黑框
#
# 两种来源：
#   1) 用 python.exe 跑源码（或双击 start.bat 由 cmd 拉起 python.exe）时，
#      Windows 会给进程配一个控制台窗口 —— 就是用户看到的"一闪而过的小窗"。
#   2) 打包成 exe（--windowed）时本就没有控制台，这里就是空操作。
#
# 关键点：必须先 ShowWindow(SW_HIDE) 立刻把窗口藏起来。
# 只调 FreeConsole 是不够的 —— 从 start.bat 启动时控制台被 cmd.exe 和
# python.exe 共享，GetConsoleProcessList 返回 2，此时 FreeConsole 不能调
#（会影响父进程），结果窗口一直留在屏幕上。
# ---------------------------------------------------------------------------
def _suppress_console():
    if os.name != "nt":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        u32 = ctypes.windll.user32
        hwnd = k32.GetConsoleWindow()
        if hwnd:
            u32.ShowWindow(hwnd, 0)          # SW_HIDE：立刻不可见
        try:
            n = k32.GetConsoleProcessList(None, 0)
        except Exception:
            n = 0
        # 只有独占控制台（自己就是那个窗口的主人）时才彻底摘掉它，
        # 避免把调用方的终端一起关掉。
        if n == 1 and not getattr(sys, "frozen", False):
            k32.FreeConsole()
    except Exception:
        pass


_suppress_console()

import ctypes  # noqa: E402,F401  （供 enable_dpi_awareness 等后续使用）

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