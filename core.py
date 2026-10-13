"""
file_utils.py —— 文件系统工具层
把所有的磁盘操作集中在这里，UI 层只调用它，方便以后换实现或加测试。
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont

# ---------------------------------------------------------------- 图标 / 主题

EXT_ICON_COLORS = {
    "图片": "#e91e63", "视频": "#9c27b0", "音频": "#00acc1",
    "文档": "#2196f3", "表格": "#4caf50", "压缩": "#ff9800",
    "代码": "#607d8b", "安装包": "#795548", "文本": "#607d8b",
}

EXT_COLOR_MAP = {
    # 图片
    ".jpg": "图片", ".jpeg": "图片", ".png": "图片", ".gif": "图片",
    ".bmp": "图片", ".webp": "图片", ".svg": "图片", ".ico": "图片", ".heic": "图片",
    # 视频
    ".mp4": "视频", ".mkv": "视频", ".avi": "视频", ".mov": "视频",
    ".wmv": "视频", ".flv": "视频", ".webm": "视频",
    # 音频
    ".mp3": "音频", ".wav": "音频", ".flac": "音频", ".aac": "音频",
    ".ogg": "音频", ".m4a": "音频",
    # 文档
    ".doc": "文档", ".docx": "文档", ".pdf": "文档", ".ppt": "文档",
    ".pptx": "文档", ".txt": "文本", ".md": "文本", ".rtf": "文档",
    # 表格
    ".xls": "表格", ".xlsx": "表格", ".csv": "表格", ".et": "表格",
    # 压缩
    ".zip": "压缩", ".rar": "压缩", ".7z": "压缩", ".tar": "压缩", ".gz": "压缩",
    # 代码
    ".py": "代码", ".js": "代码", ".ts": "代码", ".java": "代码",
    ".cpp": "代码", ".h": "代码", ".go": "代码", ".rs": "代码",
    ".html": "代码", ".css": "代码", ".json": "代码", ".xml": "代码",
    ".sh": "代码", ".bat": "代码", ".yml": "代码", ".yaml": "代码", ".toml": "代码",
    # 安装包
    ".exe": "安装包", ".msi": "安装包", ".apk": "安装包", ".dmg": "安装包",
}


def human_size(num: int) -> str:
    """把字节数变成人类可读的字符串。"""
    if num is None:
        return ""
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < step:
            if unit == "B":
                return f"{int(num)} {unit}"
            return f"{num:.1f} {unit}"
        num /= step
    return f"{num:.1f} PB"


def _make_pixmap(kind: str, is_dir: bool, size: int = 48) -> QPixmap:
    """按类型画一个扁平化图标，避免依赖外部资源文件。"""
    pm = QPixmap(size, size)
    pm.fill(Qt_transparent := QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if is_dir:
        # 文件夹：后面一个浅色主体，前面一个深色标签
        body = QColor("#FFB74D")
        back = QColor("#FFA726")
        p.setBrush(back)
        p.setPen(Qt_pen := QColor(0, 0, 0, 0))
        p.drawRoundedRect(int(size * 0.10), int(size * 0.28),
                          int(size * 0.80), int(size * 0.56), 6, 6)
        p.setBrush(body)
        p.drawRoundedRect(int(size * 0.06), int(size * 0.20),
                          int(size * 0.34), int(size * 0.14), 4, 4)
        p.setBrush(QColor("#FFE0B2"))
        p.drawRoundedRect(int(size * 0.06), int(size * 0.40),
                          int(size * 0.88), int(size * 0.44), 6, 6)
    else:
        color = QColor(EXT_ICON_COLORS.get(kind, "#90A4AE"))
        # 纸张
        p.setPen(QColor("#B0BEC5"))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(int(size * 0.20), int(size * 0.08),
                          int(size * 0.60), int(size * 0.84), 5, 5)
        # 彩色标签条
        p.setPen(color)
        p.setBrush(color)
        p.drawRoundedRect(int(size * 0.20), int(size * 0.08),
                          int(size * 0.60), int(size * 0.22), 5, 5)
        p.setBrush(QColor("#ECEFF1"))
        p.setPen(QColor("#CFD8DC"))
        for i in range(3):
            y = int(size * (0.42 + i * 0.14))
            p.drawLine(int(size * 0.30), y, int(size * 0.70), y)
    p.end()
    return pm


_icon_cache: dict[tuple, QIcon] = {}


def icon_for(path: str, is_dir: bool, size: int = 48) -> QIcon:
    """带缓存的图标获取，列表滚动时不会重复绘制。"""
    if is_dir:
        key = ("dir", size)
    else:
        ext = os.path.splitext(path)[1].lower()
        key = (EXT_COLOR_MAP.get(ext, "其他"), size)
    if key not in _icon_cache:
        _icon_cache[key] = QIcon(_make_pixmap(key[0] if not is_dir else "dir",
                                               is_dir, size))
    return _icon_cache[key]


def is_hidden(path: str, name: str) -> bool:
    if name.startswith("."):
        return True
    if os.name == "nt":
        try:
            attrs = os.stat(path).st_file_attributes
            return bool(attrs & stat.FILE_ATTRIBUTE_HIDDEN)
        except (OSError, AttributeError):
            return False
    return False


def kind_of(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    return EXT_COLOR_MAP.get(ext, "其他")


# ---------------------------------------------------------------- 后台任务

class Worker(QThread):
    """把耗时的磁盘操作挪到线程里，保证界面不卡。"""

    class DeleteDone(QObject):
        finished = Signal(list)
        failed = Signal(str, str)  # name, reason

    class CopyDone(QObject):
        progress = Signal(int, int, str)   # done, total, current
        finished = Signal(int, int)        # success, failed
        failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._task = None

    # -- 删除 --
    def do_delete(self, paths: list[str], trash: bool = True):
        """排队一次删除任务并启动线程。"""
        if not paths:
            return
        self._task = ("delete", list(paths), trash)
        self.start()

    def _run_delete(self, paths, trash):
        for p in paths:
            try:
                if trash:
                    send2trash(p)
                else:
                    if os.path.isdir(p) and not os.path.islink(p):
                        shutil.rmtree(p)
                    else:
                        os.remove(p)
                self.delete_sig.finished.emit(p)
            except Exception as e:  # 单个失败不影响其它
                self.delete_sig.failed.emit(p, str(e))

    # -- 复制 --
    def do_copy(self, sources: list[str], dest_dir: str):
        if not sources:
            return
        self._task = ("copy", list(sources), dest_dir)
        self.start()

    def _run_copy(self, sources, dest_dir):
        # 预先统计总文件数，用于进度条
        total = 0
        plans = []
        for src in sources:
            dst = os.path.join(dest_dir, os.path.basename(src.rstrip("/\\")))
            dst = _unique(dst)
            plans.append((src, dst))
            total += _count_files(src)
        done, ok, bad = 0, 0, 0
        for src, dst in plans:
            try:
                self.copy_sig.progress.emit(done, total, os.path.basename(src))
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                ok += 1
                done += _count_files(src)
            except Exception:
                bad += 1
        self.copy_sig.finished.emit(ok, bad)

    def run(self):
        if not self._task:
            return
        kind, a, b = self._task
        try:
            if kind == "delete":
                self._run_delete(a, b)
            elif kind == "copy":
                self._run_copy(a, b)
        finally:
            self._task = None


def _unique(path: str) -> str:
    """目标已存在时自动加 (1)(2) 后缀。"""
    if not os.path.exists(path):
        return path
    d, base = os.path.split(path)
    stem, ext = os.path.splitext(base)
    i = 1
    while os.path.exists(os.path.join(d, f"{stem}({i}){ext}")):
        i += 1
    return os.path.join(d, f"{stem}({i}){ext}")


def _count_files(path: str) -> int:
    if os.path.isfile(path):
        return 1
    n = 0
    for _, _, files in os.walk(path):
        n += len(files)
    return max(n, 1)


def send2trash(path: str) -> None:
    """丢进回收站。优先用系统自带的 way，失败再退回永久删除。"""
    if os.name == "nt":
        # Windows: 用 PowerShell 的 Shell.Application 走回收站
        ps = ("$shell = New-Object -ComObject Shell.Application; "
              "$item = $shell.Namespace(0).ParseName("
              f"'{path}'); $item.InvokeVerb('delete')")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, timeout=30)
        # Shell 的 delete 是异步的，等一小会儿确认文件是否真的走了
        for _ in range(20):
            if not os.path.exists(path):
                return
            import time
            time.sleep(0.15)
        raise RuntimeError("移动到回收站失败")
    else:
        from send2trash import send2trash as _s
        _s(path)


def open_in_explorer(path: str) -> None:
    """在系统文件管理器中打开；文件则用默认程序。"""
    if os.path.isdir(path):
        if os.name == "nt":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    else:
        if os.name == "nt":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


def open_terminal(path: str) -> None:
    """在当前目录开一个命令行窗口。"""
    if os.name == "nt":
        cmd = os.environ.get("COMSPEC", "cmd.exe")
        subprocess.Popen(f'start "cmd" /d "{path}" {cmd}', shell=True)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Terminal", path])
    else:
        subprocess.Popen(["x-terminal-emulator", "--working-directory", path])


# ---------------------------------------------------------------- 目录模型

@dataclass
class DirScan:
    """一次目录扫描的结果。"""
    path: str
    files: list = field(default_factory=list)     # [(name, fullpath, size, mtime)]
    dirs: list = field(default_factory=list)      # [(name, fullpath)]
    error: str = ""
    truncated: bool = False
    total_items: int = 0
    total_size: int = 0


def scan_dir(path: str, show_hidden: bool = False, limit: int = 20000) -> DirScan:
    """扫描目录。超大目录只取前 limit 项，避免界面卡死。"""
    result = DirScan(path=path)
    try:
        with os.scandir(path) as it:
            for i, entry in enumerate(it):
                if i >= limit:
                    result.truncated = True
                    break
                try:
                    if not show_hidden and is_hidden(entry.path, entry.name):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        result.dirs.append((entry.name, entry.path))
                    else:
                        st = entry.stat(follow_symlinks=False)
                        result.files.append(
                            (entry.name, entry.path, st.st_size, st.st_mtime))
                        result.total_size += st.st_size
                except (OSError, PermissionError):
                    continue
    except PermissionError:
        result.error = "无权限访问此目录"
    except FileNotFoundError:
        result.error = "目录不存在"
    except Exception as e:
        result.error = str(e)
    result.total_items = len(result.files) + len(result.dirs)
    return result


def unique_name(path: str) -> str:
    return _unique(path)