"""枚举指定进程的所有顶层窗口，确认 exe 是否真的创建了 GUI 窗口。"""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

EnumWindowsProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def windows_for_pid(target_pid: int):
    found = []

    def cb(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == target_pid:
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 2)
            user32.GetWindowTextW(hwnd, buf, n + 2)
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls, 256)
            found.append({
                "hwnd": hwnd,
                "visible": bool(user32.IsWindowVisible(hwnd)),
                "class": cls.value,
                "title": buf.value,
            })
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def main():
    EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "dist", "QtExplorer", "QtExplorer.exe")
    if not os.path.isfile(EXE):
        print("exe 不存在")
        return 1

    print("启动:", EXE)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 1        # SW_SHOWNORMAL，正常显示
    proc = subprocess.Popen(
        [EXE, "C:\\"],
        startupinfo=si,
        cwd=os.path.dirname(EXE),
    )
    print("pid:", proc.pid)

    # onefile 会先起一个解包进程，再 fork 出真正的 GUI 进程，
    # 所以要连续几秒轮询所有同名进程。
    seen_pids = {proc.pid}
    for tick in range(14):
        time.sleep(1)
        if proc.poll() is not None:
            print(f"  [{tick+1}s] 主进程已退出, code={proc.returncode}")
            break
        print(f"  [{tick+1}s] 运行中")
        # 通过进程名再找一次，覆盖 fork 出来的子进程
        try:
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq QtExplorer.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10)
            for line in out.stdout.splitlines():
                if '"QtExplorer.exe"' in line:
                    parts = [p.strip('" ') for p in line.split('","')]
                    try:
                        seen_pids.add(int(parts[1]))
                    except (IndexError, ValueError):
                        pass
        except Exception:
            pass

    print()
    print(f"找到 {len(seen_pids)} 个 QtExplorer 进程: {sorted(seen_pids)}")
    print()
    all_windows = []
    for pid in sorted(seen_pids):
        wins = windows_for_pid(pid)
        if not wins:
            print(f"  PID {pid}: 无顶层窗口")
            continue
        for w in wins:
            all_windows.append(w)
            print(f"  PID {pid}: visible={w['visible']!s:<5} "
                  f"class={w['class']:<24} title='{w['title']}'")

    print()
    visible = [w for w in all_windows if w["visible"]]
    console = [w for w in all_windows if "ConsoleWindowClass" in w["class"]]

    if visible:
        print(f">>> 有 {len(visible)} 个可见窗口，GUI 正常显示")
        for w in visible:
            print(f"      '{w['title']}'")
    else:
        print(">>> 没有可见窗口 —— GUI 未成功显示")

    if console:
        print(f">>>!! 检测到控制台窗口 {len(console)} 个，说明 --windowed 未生效")
    else:
        print(">>> 无控制台窗口（--windowed 生效）")

    # 清理
    for pid in seen_pids:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=10)
        except Exception:
            pass
    return 0 if visible and not console else 2


if __name__ == "__main__":
    sys.exit(main())