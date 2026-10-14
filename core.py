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

from PySide6.QtCore import QObject, QThread, Signal, QDir, QPoint
from PySide6.QtGui import (QIcon, QPixmap, QColor, QPainter, QPen, QFont,
                          QPolygon)

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


def _no_window_kwargs() -> dict:
    """
    隐藏子进程的控制台窗口。

    CREATE_NO_WINDOW 只在创建时带才有效，它同时保证不会闪出黑框。
    不这么做的后果：调用 PowerShell 时控制台会闪一下，
    在 GUI 程序里非常显眼（用户以为程序出问题了）。
    """
    if os.name != "nt":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE       # 0 = SW_HIDE
    return {
        "startupinfo": si,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    }


def send2trash(path: str) -> None:
    """丢进回收站。优先用系统自带的 way，失败再退回永久删除。"""
    if os.name == "nt":
        # Windows: 用 PowerShell 的 Shell.Application 走回收站。
        # 必须隐藏窗口，否则每删一次就闪一个控制台黑框。
        ps = ("$shell = New-Object -ComObject Shell.Application; "
              "$item = $shell.Namespace(0).ParseName("
              f"'{path}'); $item.InvokeVerb('delete')")
        r = subprocess.run(["powershell", "-NoProfile", "-WindowStyle",
                            "Hidden", "-Command", ps],
                           capture_output=True, timeout=30,
                           **_no_window_kwargs())
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
        # 直接用 CREATE_NEW_CONSOLE 起 cmd，并把它自己的工作目录设成目标目录。
        # 早先写成 shell=True + start "cmd" /d ...，会先拉起一个中间 cmd.exe
        #（用户看到的就是闪一下的黑框）再去开目标窗口。开新控制台只有一个
        # 窗口，没有中间层。
        subprocess.Popen(
            [cmd], cwd=path,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10))
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


# ---------------------------------------------------------------- 驱动器

@dataclass
class DriveInfo:
    """一个可访问的磁盘 / 卷。"""
    name: str          # 显示名，如 "系统盘 (C:)"
    root: str          # 根路径，如 "C:\\"
    label: str = ""    # 卷标
    fstype: str = ""   # 文件系统
    total: int = 0     # 总字节
    free: int = 0      # 剩余字节
    kind: str = "disk" # disk / cdrom / removable / network / home


def _pretty_volume_label(root: str) -> str:
    """用 Win32 API 读卷标，失败就退回盘符。"""
    if os.name != "nt":
        return ""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(261)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root), buf, 260,
            None, None, None, None, 0)
        return buf.value if ok else ""
    except Exception:
        return ""


def list_drives() -> list[DriveInfo]:
    """
    枚举所有可用卷。用 QStorageInfo 而不是 os.listdir，因为它能拿到
    卷标、文件系统类型和容量，这些对用户是有用信息。
    """
    from PySide6.QtCore import QStorageInfo, QStandardPaths

    out: list[DriveInfo] = []

    # 常用目录做成快捷入口。PySide6 里 QDir 没有 desktopPath()，
    # 这类位置统一走 QStandardPaths。
    loc = QStandardPaths.StandardLocation
    quick = [
        (QDir.homePath(), "主目录"),
        (QStandardPaths.writableLocation(loc.DesktopLocation), "桌面"),
        (QStandardPaths.writableLocation(loc.DownloadLocation), "下载"),
        (QStandardPaths.writableLocation(loc.DocumentsLocation), "文档"),
        (QStandardPaths.writableLocation(loc.MusicLocation), "音乐"),
        (QStandardPaths.writableLocation(loc.MoviesLocation), "视频"),
        (QStandardPaths.writableLocation(loc.PicturesLocation), "图片"),
    ]
    seen = set()
    for path, name in quick:
        if path and path not in seen and os.path.isdir(path):
            seen.add(path)
            out.append(DriveInfo(name=name, root=path, kind="home"))

    for si in QStorageInfo.mountedVolumes():
        root = si.rootPath()
        if os.name == "nt":
            # Windows 上 root 形如 "C:/"，统一成反斜杠便于 os.path 使用
            root = root.replace("/", "\\")
            if len(root) == 3 and root[1] == ":":
                root += "\\"

        d = DriveInfo(name=root.rstrip("\\") or root, root=root)
        d.label = si.displayName()
        # Qt 6 的 fileSystemType() 返回 QByteArray，必须转成 str，
        # 否则 tooltip 里会显示成 b'NTFS'
        fst = si.fileSystemType()
        d.fstype = bytes(fst).decode("utf-8", "replace") if fst else ""
        d.total = si.bytesTotal()
        d.free = si.bytesAvailable()

        if os.name != "nt":
            if not os.path.isdir(root):
                continue          # 未挂载的空槽位
            d.kind = "disk"
        elif si.isReadOnly():
            d.kind = "cdrom"
        elif os.access(root, os.W_OK):
            d.kind = "disk"
        else:
            d.kind = "removable"

        label = _pretty_volume_label(root)
        # QStorageInfo.displayName() 在无卷标时会返回 "D:/" 这种路径，
        # 拿它当卷标会让显示变成 "D:/ (D:)"，必须过滤掉
        if (label and label not in ("", "System Volume Information")
                and label not in (root, root.rstrip("\\"))):
            d.name = f"{label} ({d.name})"
        if d.kind == "cdrom" and not label:
            d.name = f"光驱 ({d.name})"

        out.append(d)

    # 可写磁盘排前面，同类按盘符排
    def order(d: DriveInfo):
        kind_rank = {"disk": 0, "removable": 1, "network": 2, "cdrom": 3}
        return (kind_rank.get(d.kind, 4), d.root.upper())

    drives = [d for d in out if d.kind != "home"]
    homes = [d for d in out if d.kind == "home"]
    return homes + sorted(drives, key=order)


def drive_icon_pixmap(d: DriveInfo, size: int = 24) -> QPixmap:
    """按驱动器类型画图标：磁盘 / U盘 / 光驱 / 网络。"""
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    palette = {"disk": ("#42A5F5", "#1E88E5"),
               "removable": ("#66BB6A", "#43A047"),
               "cdrom": ("#AB47BC", "#8E24AA"),
               "network": ("#FFA726", "#FB8C00"),
               "home": ("#78909C", "#546E7A")}
    light, dark = palette.get(d.kind, palette["disk"])

    if d.kind == "home":
        # 房子轮廓：墙身 + 屋顶，整体占满画布以免太小看不清
        p.setPen(QPen(QColor(dark), 1.2))
        p.setBrush(QColor(light))
        cx = size / 2
        roof_y = size * 0.16
        wall_top = size * 0.52
        wall_bottom = size * 0.88
        half = size * 0.30
        p.drawPolygon(QPolygon([
            QPoint(int(cx), int(roof_y)),
            QPoint(int(cx + half + size * 0.07), int(wall_top)),
            QPoint(int(cx + half), int(wall_top)),
            QPoint(int(cx + half), int(wall_bottom)),
            QPoint(int(cx - half), int(wall_bottom)),
            QPoint(int(cx - half), int(wall_top)),
            QPoint(int(cx - half - size * 0.07), int(wall_top)),
        ]))
    else:
        # 驱动器盒体
        p.setPen(QColor(dark))
        p.setBrush(QColor(light))
        p.drawRoundedRect(int(size * 0.10), int(size * 0.30),
                          int(size * 0.80), int(size * 0.46), 4, 4)
        p.setBrush(QColor("#ECEFF1"))
        p.setPen(QColor(dark))
        if d.kind == "cdrom":
            p.drawEllipse(int(size * 0.32), int(size * 0.38),
                          int(size * 0.36), int(size * 0.14))
        else:
            p.drawRect(int(size * 0.68), int(size * 0.46),
                       int(size * 0.10), int(size * 0.10))
    p.end()
    return pm

# ---------------------------------------------------------------- 预览面板

@dataclass
class PreviewInfo:
    """预览窗格的数据：一个文件夹的第一层内容。"""
    path: str
    dirs: list = field(default_factory=list)   # [(name, fullpath)]
    files: list = field(default_factory=list)  # [(name, size, mtime)]
    total_items: int = 0
    total_size: int = 0
    file_count: int = 0
    dir_count: int = 0
    error: str = ""
    truncated: bool = False
    # 递归估算的总文件数/总大小（只走一层子目录，用于"文件夹属性"）
    deep_files: int = 0
    deep_bytes: int = 0
    deep_truncated: bool = False


def scan_preview(path: str, show_hidden: bool = False,
                 limit: int = 200) -> PreviewInfo:
    """
    扫描用于预览的目录信息。只取当前一层，最多 limit 项；
    同时统计下级目录的累计文件数与大小（有上限，避免卡死）。
    """
    info = PreviewInfo(path=path)
    if not os.path.isdir(path):
        info.error = "不是文件夹"
        return info

    sub_dirs: list[str] = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                if len(info.dirs) + len(info.files) >= limit:
                    info.truncated = True
                    break
                try:
                    if not show_hidden and is_hidden(entry.path, entry.name):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        info.dirs.append((entry.name, entry.path))
                        sub_dirs.append(entry.path)
                    else:
                        st = entry.stat(follow_symlinks=False)
                        info.files.append(
                            (entry.name, st.st_size, st.st_mtime))
                        info.total_size += st.st_size
                        info.file_count += 1
                except (OSError, PermissionError):
                    continue
    except PermissionError:
        info.error = "无权限访问"
        return info
    except Exception as e:
        info.error = str(e)
        return info

    info.dir_count = len(info.dirs)
    info.total_items = info.file_count + info.dir_count

    # 下一层各子目录的文件数与大小，最多下探 3 层且限定总耗时
    budget = [8000]           # 最多累计统计 8000 个文件
    for d in sub_dirs[:40]:  # 最多看 40 个子目录
        if budget[0] <= 0:
            info.deep_truncated = True
            break
        _count_dir(d, budget, info)

    return info


def _count_dir(path: str, budget: list, info: PreviewInfo,
               depth: int = 0, max_depth: int = 3) -> None:
    """递归累计文件数与大小，budget 用尽即停。"""
    if depth > max_depth:
        info.deep_truncated = True
        return
    try:
        with os.scandir(path) as it:
            for entry in it:
                if budget[0] <= 0:
                    info.deep_truncated = True
                    return
                try:
                    if is_hidden(entry.path, entry.name):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        _count_dir(entry.path, budget, info,
                                   depth + 1, max_depth)
                    else:
                        budget[0] -= 1
                        info.deep_files += 1
                        info.deep_bytes += entry.stat(
                            follow_symlinks=False).st_size
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass


# ---------------------------------------------------------------- 收藏夹

def _fav_path() -> str:
    """收藏夹数据文件位置：%APPDATA%/QtExplorer/favorites.json。"""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "QtExplorer")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return os.path.join(d, "favorites.json")


def load_favorites() -> list[str]:
    """读取收藏夹列表，按保存顺序。路径不存在会被自动剔除。"""
    import json
    try:
        with open(_fav_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for p in data:
        if isinstance(p, str) and os.path.exists(p) and p not in out:
            out.append(p)
    return out


def save_favorites(paths: list[str]) -> None:
    """保存收藏夹列表。"""
    import json
    try:
        with open(_fav_path(), "w", encoding="utf-8") as f:
            json.dump(list(paths), f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def add_favorite(path: str) -> bool:
    """加入收藏，返回是否新加。"""
    path = os.path.abspath(path)
    favs = load_favorites()
    if path in favs:
        return False
    favs.append(path)
    save_favorites(favs)
    return True


def remove_favorite(path: str) -> bool:
    """移出收藏，返回是否确实移除了。"""
    path = os.path.abspath(path)
    favs = load_favorites()
    if path not in favs:
        return False
    favs.remove(path)
    save_favorites(favs)
    return True


def toggle_favorite(path: str) -> bool:
    """切换收藏状态，返回切换后是否为已收藏。"""
    path = os.path.abspath(path)
    if path in load_favorites():
        remove_favorite(path)
        return False
    add_favorite(path)
    return True
