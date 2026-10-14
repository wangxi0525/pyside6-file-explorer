"""verify_pack.py —— 对打包出的 exe 做真机体检。

覆盖用户反馈的两个场景：
  1) 启动瞬间有没有闪出小空窗；
  2) 单击 D:\\迅雷下载 时有没有连闪小黑窗。

做法：SetWinEventHook 全程记录 exe 进程创建的每个顶层窗口，
把"尺寸异常小"且"可见"的窗口列为嫌疑。
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(BASE, sys.argv[1] if len(sys.argv) > 1 else "dist_pack",
                   "QtExplorer", "QtExplorer.exe")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EVENT_OBJECT_CREATE = 0x8000
OBJID_WINDOW = 0
WinEventProcType = ctypes.WINFUNCTYPE(
    None, wt.HANDLE, wt.DWORD, wt.HWND, wt.LONG, wt.LONG, wt.DWORD, wt.DWORD)

TARGET_PIDS = set()
EV = []
_cb = []
T0 = None


def on_event(hook, event, hwnd, id_obj, id_child, tid, msec):
    if id_obj != OBJID_WINDOW or id_child != 0 or not hwnd:
        return
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value not in TARGET_PIDS:
        return
    c = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, c, 256)
    cls = c.value
    # 忽略 Qt 自建的内部窗口（剪贴板/屏幕观察/电源/主题/标题栏）
    if cls in ("Qt6120ClipboardView", "Qt6120ScreenChangeObserverWindow",
               "Qt6120ThemeChangeObserverWindow", "Qt6120PowerDummyWindow",
               "_q_titlebar", "Qt6120QWindowToolTipSaveBits"):
        return
    tb = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, tb, 256)
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    EV.append((round(time.time() - T0, 3), cls, tb.value,
               r.right - r.left, r.bottom - r.top,
               bool(user32.IsWindowVisible(hwnd))))


def hook_thread():
    proc = WinEventProcType(on_event)
    _cb.append(proc)
    user32.SetWinEventHook(EVENT_OBJECT_CREATE, EVENT_OBJECT_CREATE, 0, proc,
                           0, 0, 0)
    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def pids_of(name="QtExplorer.exe"):
    out = set()
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
            capture_output=True, timeout=10)
        text = r.stdout.decode("utf-8", "replace")
        for line in text.splitlines():
            if f'"{name}"' in line:
                parts = [p.strip('" ') for p in line.split('","')]
                try:
                    out.add(int(parts[1]))
                except (IndexError, ValueError):
                    pass
    except Exception:
        pass
    return out


def main():
    global T0, TARGET_PIDS
    if not os.path.isfile(EXE):
        print("exe 不存在:", EXE)
        return 1

    # 清场
    for pid in pids_of():
        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       capture_output=True)
    time.sleep(0.6)

    threading.Thread(target=hook_thread, daemon=True).start()
    time.sleep(0.35)

    print("启动:", EXE)
    T0 = time.time()
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 1
    proc = subprocess.Popen([EXE, "D:\\"], startupinfo=si,
                            cwd=os.path.dirname(EXE))
    TARGET_PIDS.add(proc.pid)
    print("pid:", proc.pid)

    # 跟踪可能 fork 出的子进程
    for _ in range(20):
        time.sleep(0.35)
        TARGET_PIDS |= pids_of()
        if proc.poll() is not None:
            break

    print(f"目标进程: {sorted(TARGET_PIDS)}")
    print(f"\n===== 顶层窗口创建事件（{len(EV)} 个）=====")
    for t, cls, title, w, h, v in EV:
        print(f"  [{t:6.3f}s] {cls:26s} {w:>4}x{h:<4} vis={int(v)} "
              f"title={title!r}")

    small = [e for e in EV if 0 < e[3] < 500 and 0 < e[4] < 400 and e[5]]
    print(f"\n===== 嫌疑：小尺寸可见窗口（{len(small)} 个）=====")
    for t, cls, title, w, h, v in small:
        print(f"  ★ [{t:6.3f}s] {cls} {w}x{h} title={title!r}")
    if not small:
        print("  （无）")

    big = [e for e in EV if e[3] > 500]
    print(f"\n正常尺寸窗口 {len(big)} 个（主窗口）")

    for pid in TARGET_PIDS:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       capture_output=True)
    ok = len(small) == 0 and len(big) >= 1
    print("\n" + (">>> ✅ 通过：无小窗闪烁，主窗口正常" if ok
                  else ">>> ❌ 未通过"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
