"""
main_window.py —— 主窗口与界面逻辑
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

from PySide6.QtCore import (Qt, QDir, QSize, QTimer, QStandardPaths,
                            QPropertyAnimation, QEasingCurve, Signal,
                            QThread, QObject, QMetaObject, Q_ARG, Slot,
                            QRectF)
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices,
                           QDragEnterEvent, QDropEvent, QGuiApplication,
                           QKeySequence, QIcon, QPainter, QPen, QPixmap)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFileSystemModel, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QPushButton, QSplitter, QStackedWidget, QStatusBar,
    QScrollArea,
    QSizePolicy,
    QTableWidget, QTableWidgetItem, QToolBar, QToolButton, QToolTip,
    QVBoxLayout, QWidget, QAbstractItemView as AIV)

from core import (DirScan, DriveInfo, PreviewInfo, Worker, drive_icon_pixmap,
                  human_size, icon_for, is_hidden, kind_of, list_drives,
                  open_in_explorer, open_terminal, scan_dir, scan_preview,
                  send2trash, unique_name, EXT_COLOR_MAP,
                  load_favorites, save_favorites, add_favorite,
                  remove_favorite, toggle_favorite)

APP_NAME = "Qt 资源管理器"
APP_VERSION = "1.2"


# ---------------------------------------------------------------- 主题

def _theme_path() -> str:
    """主题配置文件：%APPDATA%/QtExplorer/theme.json"""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "QtExplorer")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return os.path.join(d, "theme.json")


def load_theme() -> str:
    """读取主题名，默认 light。"""
    import json
    try:
        with open(_theme_path(), encoding="utf-8") as f:
            v = json.load(f)
        return v.get("theme", "light")
    except (OSError, ValueError, AttributeError):
        return "light"


def save_theme(name: str) -> None:
    """保存主题名。"""
    import json
    try:
        with open(_theme_path(), "w", encoding="utf-8") as f:
            json.dump({"theme": name}, f)
    except OSError:
        pass


# 配色表：深浅两套。新增控件只需在这里加一个键，
# 不必维护两份完整样式表。
THEMES = {
    "light": {
        "bg": "#FFFFFF", "alt_bg": "#FAFAFA", "fg": "#37474F",
        "muted": "#90A4AE", "dim": "#607D8B", "faint": "#B0BEC5",
        "border": "#DDE3E9", "grid": "#EEEEEE", "border2": "#E0E0E0",
        "accent": "#1565C0", "accent_bg": "#BBDEFB",
        "hover": "#E3F2FD", "accent2": "#64B5F6",
        "sel_fg": "#0D47A1", "bar_bg": "#E3E7EA",
        "dir_fg": "#1565C0", "file_fg": "#546E7A",
    },
    "dark": {
        "bg": "#1E2429", "alt_bg": "#232A31", "fg": "#CFD8DC",
        "muted": "#7E8B94", "dim": "#90A4AE", "faint": "#5A666E",
        "border": "#333C44", "grid": "#2A3238", "border2": "#3A444C",
        "accent": "#64B5F6", "accent_bg": "#2C4A63",
        "hover": "#2A3540", "accent2": "#1976D2",
        "sel_fg": "#90CAF9", "bar_bg": "#333C44",
        "dir_fg": "#64B5F6", "file_fg": "#B0BEC5",
    },
}


def build_qss(c: dict) -> str:
    """由配色字典生成全局样式表。"""
    return f"""
    QWidget {{ background:{c['bg']}; color:{c['fg']}; font-size:13px; }}
    QListWidget, QTableWidget {{
        background:{c['bg']}; alternate-background-color:{c['alt_bg']}; }}
    QListWidget::item {{ color:{c['fg']}; }}
    QListWidget::item:selected, QTableWidget::item:selected {{
        background:{c['accent_bg']}; color:{c['sel_fg']}; }}
    QListWidget::item:hover {{ background:{c['hover']}; }}
    QTableWidget {{ gridline-color:{c['grid']}; }}
    QHeaderView::section {{
        background:{c['alt_bg']}; color:{c['dim']}; padding:6px; border:none;
        border-bottom:1px solid {c['border2']};
        border-right:1px solid {c['grid']}; }}
    QToolButton {{ color:{c['dim']}; background:transparent; border:none;
                  border-radius:6px; font-size:15px; }}
    QToolButton:hover {{ background:{c['hover']}; color:{c['accent']}; }}
    QToolButton:disabled {{ color:{c['faint']}; }}
    QLineEdit {{ background:{c['bg']}; color:{c['fg']};
                border:1px solid {c['border']}; border-radius:6px;
                padding:5px 8px; }}
    QLineEdit:focus {{ border:1px solid {c['accent2']}; }}
    QPushButton {{ background:{c['bg']}; color:{c['fg']};
                  border:1px solid {c['border']}; border-radius:6px;
                  padding:6px 12px; }}
    QPushButton:hover {{ background:{c['hover']};
                         border-color:{c['accent_bg']}; }}
    QDialogButtonBox QPushButton {{ min-width:72px; }}
    QMenu {{ background:{c['bg']}; border:1px solid {c['border2']};
             padding:4px; }}
    QMenu::item {{ padding:7px 24px 7px 12px; border-radius:4px; }}
    QMenu::item:selected {{ background:{c['hover']}; color:{c['accent']}; }}
    QMenu::separator {{ height:1px; background:{c['grid']};
                       margin:4px 8px; }}
    QStatusBar {{ background:{c['alt_bg']}; color:{c['muted']}; }}
    QProgressBar {{ border:1px solid {c['border2']}; border-radius:4px;
                   background:{c['bg']}; text-align:center;
                   color:{c['dim']}; }}
    QProgressBar::chunk {{ background:{c['accent2']}; border-radius:3px; }}
    QScrollBar:vertical {{ background:{c['alt_bg']}; width:10px; margin:0; }}
    QScrollBar:handle:vertical {{ background:{c['border2']};
                                 border-radius:5px; min-height:30px; }}
    QScrollBar:handle:vertical:hover {{ background:{c['muted']}; }}
    QScrollBar:add-line, QScrollBar:sub-line {{ height:0; width:0; }}
    QScrollBar:horizontal {{ background:{c['alt_bg']}; height:10px; }}
    QScrollBar:handle:horizontal {{ background:{c['border2']};
                                   border-radius:5px; min-width:30px; }}
    QScrollBar:add-page, QScrollBar:sub-page {{ background:transparent; }}
    QLabel {{ background:transparent; }}
    QToolTip {{ background:{c['alt_bg']}; color:{c['fg']};
                border:1px solid {c['border2']}; padding:4px 6px; }}
    QSplitter::handle {{ background:{c['grid']}; }}
    """

# 预览面板里直接显示缩略图的图片格式
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".ico"}

# ---------------------------------------------------------------- 自定义对话框

class NewFolderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建文件夹")
        self.setFixedWidth(340)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 14)
        t = QLabel("文件夹名称")
        f = QLineEdit()
        f.selectAll()
        tip = QLabel("不能包含 \\ / : * ? \" < > |")
        tip.setStyleSheet("color:#90A4AE;font-size:11px;")
        lay.addWidget(t)
        lay.addWidget(f)
        lay.addWidget(tip)
        lay.addSpacing(6)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.field = f
        f.returnPressed.connect(self.accept)

    def text(self):
        t = self.field.text().strip()
        return t if t and not any(c in t for c in '\\/:*?"<>|') else None


class GoToDialog(QDialog):
    """转到指定路径。"""
    def __init__(self, current: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("转到")
        self.setFixedWidth(520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 14)
        quick = QHBoxLayout()
        loc = QStandardPaths.StandardLocation
        for label, path in (("桌面", QStandardPaths.writableLocation(loc.DesktopLocation)),
                            ("文档", QStandardPaths.writableLocation(loc.DocumentsLocation)),
                            ("下载", QStandardPaths.writableLocation(loc.DownloadLocation)),
                            ("图片", QStandardPaths.writableLocation(loc.PicturesLocation)),
                            ("主页", QDir.homePath())):
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFlat(True)
            b.setStyleSheet("color:#1565C0;")
            b.clicked.connect(lambda _, p=path: self.field.setText(p))
            quick.addWidget(b)
        quick.addStretch()
        lay.addLayout(quick)

        lay.addWidget(QLabel("路径"))
        self.field = QLineEdit(current)
        self.field.returnPressed.connect(self.accept)
        lay.addWidget(self.field)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.history: list[str] = []


class RenameDialog(QDialog):
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("重命名")
        self.setFixedWidth(380)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 14)
        lay.addWidget(QLabel("新名称"))
        self.field = QLineEdit(name)
        # 只选中主文件名，扩展名保留
        self.field.setSelection(0, len(name.rsplit(".", 1)[0]) if "." in name else len(name))
        self.field.returnPressed.connect(self.accept)
        lay.addWidget(self.field)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.field.selectAll()

    def text(self):
        return self.field.text().strip()


class PropertiesDialog(QDialog):
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("属性")
        self.setFixedWidth(430)
        path = os.path.abspath(path)
        self.setWindowTitle(f"{os.path.basename(path) or path} 的属性")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.setSpacing(12)

        # 图标 + 名称
        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(icon_for(path, os.path.isdir(path), 64).pixmap(64, 64))
        head.addWidget(icon)
        name_box = QVBoxLayout()
        name_lbl = QLabel(os.path.basename(path) or path)
        name_lbl.setStyleSheet("font-size:15px;font-weight:600;")
        name_box.addWidget(name_lbl)
        kind = "文件夹" if os.path.isdir(path) else f"{kind_of(path)}文件"
        name_box.addWidget(QLabel(f"类型: {kind}"))
        head.addLayout(name_box, 1)
        lay.addLayout(head)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#ECEFF1;")
        lay.addWidget(sep)

        rows = QVBoxLayout()
        rows.setSpacing(6)

        def add_row(k: str, v: str):
            h = QHBoxLayout()
            a = QLabel(k)
            a.setFixedWidth(90)
            a.setStyleSheet("color:#607D8B;")
            b = QLabel(v)
            b.setWordWrap(True)
            b.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            h.addWidget(a)
            h.addWidget(b, 1)
            rows.addLayout(h)

        try:
            st = os.stat(path)
            add_row("位置", os.path.dirname(path))
            add_row("大小", f"{human_size(st.st_size)}  ({st.st_size:,} 字节)")
            add_row("包含", _describe_count(path, os.path.isdir(path)))
            add_row("创建时间", datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"))
            add_row("修改时间", datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
            add_row("访问时间", datetime.fromtimestamp(st.st_atime).strftime("%Y-%m-%d %H:%M:%S"))
            if os.path.isdir(path):
                add_row("权限", "rwx" if os.access(path, os.W_OK) else "只读")
            else:
                add_row("权限", oct(st.st_mode)[-3:])
        except OSError as e:
            add_row("错误", str(e))

        lay.addLayout(rows)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


class AboutDialog(QDialog):
    """关于对话框：显示版本、技术栈与仓库地址。"""

    REPO = "https://github.com/wangxi0525/pyside6-file-explorer"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"关于 {APP_NAME}")
        self.setFixedWidth(420)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 16)
        lay.setSpacing(14)

        head = QHBoxLayout()
        icon = QLabel()
        ico = resource_icon(96)
        if ico:
            icon.setPixmap(ico)
        head.addWidget(icon)
        col = QVBoxLayout()
        name = QLabel(APP_NAME)
        name.setStyleSheet("font-size:18px;font-weight:600;color:#37474F;")
        ver = QLabel(f"版本 {APP_VERSION}")
        ver.setStyleSheet("color:#78909C;")
        col.addWidget(name)
        col.addWidget(ver)
        head.addLayout(col, 1)
        lay.addLayout(head)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#ECEFF1;")
        lay.addWidget(sep)

        rows = QVBoxLayout()
        rows.setSpacing(7)

        def add_row(k: str, v: str):
            h = QHBoxLayout()
            a = QLabel(k)
            a.setFixedWidth(72)
            a.setStyleSheet("color:#607D8B;")
            b = QLabel(v)
            b.setWordWrap(True)
            b.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            h.addWidget(a)
            h.addWidget(b, 1)
            rows.addLayout(h)

        try:
            from PySide6 import __version__ as pyside_ver
        except Exception:
            pyside_ver = "unknown"
        add_row("技术栈", "Python + PySide6 (Qt 6)")
        add_row("PySide6", pyside_ver)
        add_row("授权", "MIT License")
        lay.addLayout(rows)

        repo = QLabel(
            f'<a href="{self.REPO}" style="color:#1565C0;">{self.REPO}</a>')
        repo.setOpenExternalLinks(True)
        repo.setWordWrap(True)
        repo.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(repo)

        lay.addStretch()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


def _resource_dir() -> str:
    """定位随包资源目录，兼容源码运行与 PyInstaller 打包。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_icon(size: int = 96):
    """读取应用图标，返回 QPixmap；找不到返回 None。"""
    path = os.path.join(_resource_dir(), "app_icon.ico")
    if not os.path.isfile(path):
        return None
    pm = QIcon(path).pixmap(size, size)
    return None if pm.isNull() else pm


def _describe_count(path: str, is_dir: bool) -> str:
    if not is_dir:
        return "1 个文件"
    try:
        f = d = 0
        for _, _, files in os.walk(path):
            f += len(files)
            d += 1
        return f"{d:,} 个文件夹, {f:,} 个文件"
    except OSError:
        return "无法统计"


# ---------------------------------------------------------------- 列表项 widget

class FileCard(QFrame):
    """大图标模式下的单个文件卡片。"""
    def __init__(self, name: str, path: str, is_dir: bool, parent=None):
        super().__init__(parent)
        self.path = path
        self.is_dir = is_dir
        self.setFixedSize(104, 116)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "FileCard{border-radius:8px;background:transparent;}"
            "FileCard:hover{background:#E3F2FD;}"
            "FileCard:selected{background:#BBDEFB;}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 6)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        ic = QLabel()
        ic.setPixmap(icon_for(path, is_dir, 48).pixmap(48, 48))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ic)

        txt = QLabel(name)
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt.setWordWrap(False)
        txt.setStyleSheet("font-size:12px;color:#37474F;")
        txt.setToolTip(path)
        # 超长名字中间省略
        f = txt.fontMetrics()
        if f.horizontalAdvance(name) > 92:
            while f.horizontalAdvance(name + "…") > 92 and len(name) > 4:
                name = name[:-1]
            txt.setText(name + "…")
        lay.addWidget(txt)
        lay.addStretch()


# ---------------------------------------------------------------- 预览扫描线程

class _PreviewScanner(QObject):
    """
    在后台线程里扫描预览目录。

    注意：request() 由 UI 线程调用，而本对象已 moveToThread 到后台线程，
    所以必须用 QMetaObject.invokeMethod 走队列，不能直接调用槽函数——
    直接调用会被 Qt 拒绝（对象不属于当前线程）。
    """

    result = Signal(str, object)     # path, PreviewInfo

    def __init__(self, show_hidden: bool = False):
        super().__init__()
        self._show_hidden = show_hidden
        self._queue: list[str] = []
        self._busy = False

    def set_show_hidden(self, flag: bool):
        """UI 线程调用，同样要排队到后台线程。"""
        QMetaObject.invokeMethod(self, "_set_hidden",
                                 Qt.ConnectionType.QueuedConnection,
                                 Q_ARG(bool, flag))

    @Slot(bool)
    def _set_hidden(self, flag: bool):
        self._show_hidden = flag

    def request(self, path: str):
        """UI 线程调用：排队到后台线程执行。"""
        QMetaObject.invokeMethod(self, "_enqueue", Qt.ConnectionType.QueuedConnection,
                                 Q_ARG(str, path))

    def cancel(self):
        QMetaObject.invokeMethod(self, "_clear", Qt.ConnectionType.QueuedConnection)

    @Slot(str)
    def _enqueue(self, path: str):
        # 连续点击时只保留最新一个请求，前面的作废
        self._queue = [path]
        self._pump()

    @Slot()
    def _clear(self):
        self._queue.clear()

    @Slot()
    def _pump(self):
        if self._busy or not self._queue:
            return
        path = self._queue.pop(0)
        self._busy = True
        try:
            info = scan_preview(path, show_hidden=self._show_hidden)
        except Exception as e:                       # 兜底，别让线程死掉
            info = PreviewInfo(path=path, error=str(e))
        self._busy = False
        self.result.emit(path, info)
        if self._queue:                # 期间又来了新请求
            self._pump()


# ---------------------------------------------------------------- 预览面板

def _small_icon(path: str, is_dir: bool, size: int = 16) -> QPixmap:
    """
    预览面板用的小图标。先按 4 倍尺寸绘制再平滑缩下来，
    直接按目标尺寸画会丢失细节（尤其文件图标里的色块和折角）。
    """
    pm = icon_for(path, is_dir, size * 4).pixmap(size * 4, size * 4)
    if pm.isNull():
        return pm
    return pm.scaled(size, size,
                     Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)


class EntryRow(QWidget):
    """
    预览面板里的一行：图标 + 名称 + 右侧大小。

    整行都是交互区域（不只文字），行为与资源管理器一致：
    悬停显示浅蓝底，单击选中并高亮，双击才打开。
    单击就打开在浏览时会误触——手扫过列表就弹出程序，很烦人。
    """

    doubleClicked = Signal(str)
    clicked = Signal(str)

    # -- 批量 tooltip 抑制 --------------------------------------------------
    # 预览重绘时会一次性给几十个条目 setToolTip。如果鼠标正好悬在某个条目
    # 上，Qt 会认为"提示内容变了"，于是把 tooltip 窗口重建一次 —— 每个条目
    # 一个，屏幕上一连串 136x50 的小黑窗一闪而过（用户反馈的"小黑窗"）。
    # 批量改动期间先压住，整批结束后只生效一次。
    _tip_batch = 0

    @classmethod
    def begin_tip_batch(cls):
        cls._tip_batch += 1

    @classmethod
    def end_tip_batch(cls):
        cls._tip_batch = max(0, cls._tip_batch - 1)

    def __init__(self, icon: QPixmap, text: str, tail: str = "",
                 color: str = "#546E7A", size: int = 11,
                 tooltip: str = "", path: str = "", is_dir: bool = False,
                 parent=None):
        super().__init__(parent)
        self.path = path
        self.is_dir_row = is_dir
        self._hover = False
        self._selected = False
        self._loading = False
        self._pending_tip = tooltip

        h = QHBoxLayout(self)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(5)

        # 注意：三个 QLabel 必须显式以 self 为父对象。
        # 无参 QLabel() 是一个【没有父对象的顶层窗口】，此时只要调用
        # setVisible(True) 或在真正布局前被 show()，屏幕上就会闪出一个
        # 独立小窗 —— 这正是"点文件夹时闪小黑窗"的根源（预览面板一次
        # 最多铺 30 行，于是连闪 30 次）。父对象在构造时给，永绝后患。
        self.ic = QLabel(self)
        if not icon.isNull():
            self.ic.setPixmap(icon)
        self.ic.setFixedSize(16, 16)
        self.ic.setStyleSheet("background:transparent;")
        h.addWidget(self.ic, 0, Qt.AlignmentFlag.AlignVCenter)

        self.name = QLabel(text, self)
        self.name.setStyleSheet(
            f"background:transparent;color:{color};font-size:{size}px;")
        # 过长时省略而不是撑破布局
        self.name.setSizePolicy(QSizePolicy.Policy.Ignored,
                                QSizePolicy.Policy.Preferred)
        h.addWidget(self.name, 1)

        self.tail = QLabel(tail, self)
        self.tail.setStyleSheet(
            "background:transparent;color:#B0BEC5;font-size:10px;")
        self.tail.setSizePolicy(QSizePolicy.Policy.Fixed,
                                QSizePolicy.Policy.Preferred)
        h.addWidget(self.tail, 0)
        # 有了父对象（且已入布局）之后，再决定它看不看得见
        self.tail.setVisible(bool(tail))

        if path:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self.set_loading(True)      # 先进入加载态，扫描完成才给 tooltip

        # 记下基础字号，重绘样式时要用
        self._size = size
        self._base_color = color

    # 整行接管鼠标事件，这样文字和图标外的空白处也能响应
    def mousePressEvent(self, e):
        if self.path:
            self.clicked.emit(self.path)
            self.set_selected(True)
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.path:
            self.doubleClicked.emit(self.path)
        super().mouseDoubleClickEvent(e)

    def enterEvent(self, e):
        self._hover = True
        self._restyle()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._restyle()
        super().leaveEvent(e)

    def _bg(self) -> str:
        if self._selected:
            return "#BBDEFB"
        if self._hover:
            return "#E3F2FD"
        return "transparent"

    def _restyle(self):
        if not self.path:
            return
        bg = self._bg()
        col = "#0D47A1" if self._selected else self._base_color
        self.ic.setStyleSheet(f"background:{bg};")
        self.name.setStyleSheet(
            f"background:{bg};color:{col};font-size:{self._size}px;")
        self.tail.setStyleSheet(
            f"background:{bg};color:#90A4AE;font-size:10px;")

    def set_selected(self, on: bool):
        self._selected = on
        self._restyle()

    def set_loading(self, loading: bool):
        """
        加载态。

        扫描进行中先不给 tooltip：后台扫描一有结果就重建整组 widget，
        鼠标恰好悬在上面时 tooltip 会反复弹出/消失，看起来就是不断
        闪现的小黑框。渲染完成后再 set_loading(False) 补上。
        """
        self._loading = loading
        if loading:
            self._tip = ""
            if not EntryRow._tip_batch:
                self.setToolTip("")
        else:
            tip = getattr(self, "_pending_tip", "")
            # 批量期间不逐个下发：每次 setToolTip 都可能让 Qt 重建
            # tooltip 窗口，鼠标悬停时就是那串一闪而过的小黑窗。
            if not EntryRow._tip_batch:
                self.setToolTip(tip)

    def set_tooltip(self, tip: str):
        """记录完整 tooltip；若仍在加载态则等加载完再生效。"""
        self._pending_tip = tip
        if not getattr(self, "_loading", False) and not EntryRow._tip_batch:
            self.setToolTip(tip)

    def flush_tooltip(self):
        """批量结束后把挂起的 tooltip 一次落地。"""
        if getattr(self, "_loading", False):
            return
        self.setToolTip(getattr(self, "_pending_tip", ""))

    def apply_theme(self, c: dict):
        """按主题重刷配色（内联样式优先级高于全局 qss，必须逐个设置）。"""
        self._base_color = c["accent"] if self.is_dir_row else c["file_fg"]
        self._restyle()

    def set_active(self, on: bool):
        """兼容旧的选中联动接口。"""
        self.set_selected(on)


class PreviewPane(QFrame):
    """
    预览窗格：选中文件夹时在右侧显示其下级内容。
    选中文件时则显示文件的基本信息。
    """

    # 预览面板里点击子文件夹 -> 主窗口导航过去
    _open_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("preview")
        self.setMinimumWidth(190)
        self.setStyleSheet(
            "QFrame#preview{background:#FAFAFA;border-left:1px solid #E0E0E0;}"
            "QLabel{background:transparent;}")

        self.path = None
        self._last_rendered = None     # 上次渲染的指纹，用于跳过重复渲染
        self._pending = None
        # 大目录扫描放后台线程，避免点一下就卡住
        self._busy = False

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 顶部：标题 + 刷新按钮
        head = QFrame()
        head.setFixedHeight(32)
        head.setStyleSheet(
            "QFrame{background:#FFFFFF;border-bottom:1px solid #EEEEEE;}")
        self._head_frame = head          # 主题切换时要重刷（夜间模式下这里
                                         # 若保持白底，预览面板就会"花"）
        hl = QHBoxLayout(head)
        hl.setContentsMargins(12, 4, 6, 4)
        self.title = QLabel("预览")
        self.title.setStyleSheet(
            "font-weight:600;color:#607D8B;background:transparent;")
        hl.addWidget(self.title)
        hl.addStretch()
        self.btn_goto = QToolButton()
        self.btn_goto.setIcon(QIcon(_arrow_pixmap("refresh", 15, "#78909C")))
        self.btn_goto.setFixedSize(24, 24)
        self.btn_goto.setToolTip("进入该文件夹")
        self.btn_goto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_goto.clicked.connect(self.goto)
        hl.addWidget(self.btn_goto)
        v.addWidget(head)

        # 滚动内容区
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background:#FAFAFA;")
        self.body = QWidget()
        self.body.setStyleSheet("background:#FAFAFA;")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(12, 10, 12, 12)
        self.body_layout.setSpacing(6)
        self.scroll.setWidget(self.body)
        v.addWidget(self.scroll, 1)

        # 空状态提示
        self.hint = QLabel("预览窗格\n\n在左侧点选一个文件夹\n这里会显示它的下级内容")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(
            "color:#90A4AE;background:#FAFAFA;font-size:12px;"
            "padding:0 14px;border:1px dashed #CFD8DC;border-radius:6px;")
        v.addWidget(self.hint, 1)
        self.scroll.setVisible(False)

        self.show_placeholder()

    # ---- 占位状态 ----
    def apply_theme(self, c: dict):
        """按主题刷新预览面板自身与内部文字。"""
        self._c = c
        self.setStyleSheet(
            f"QFrame{{background:{c['bg']};border-left:1px solid {c['grid']};}}")
        # 标题条 / 滚动区 / 内容体的底色当初写死了浅色，不重刷的话
        # 夜间模式下预览面板会出现"上半截白、下半截黑"的花屏效果
        self._head_frame.setStyleSheet(
            "QFrame{background:%s;border-bottom:1px solid %s;}"
            % (c["bg"], c["grid"]))
        self.scroll.setStyleSheet("background:%s;" % c["bg"])
        self.body.setStyleSheet("background:%s;" % c["bg"])
        self.title.setStyleSheet(
            f"background:transparent;color:{c['dim']};font-size:11px;")
        self.hint.setStyleSheet(
            f"color:{c['muted']};background:{c['bg']};font-size:12px;"
            f"padding:0 14px;border:1px dashed {c['border2']};border-radius:6px;")
        # 刷新按钮的线条图标按新主题重画（原色 #78909C 在深底上偏暗）
        self.btn_goto.setIcon(QIcon(_arrow_pixmap("refresh", 15, c["dim"])))
        for r in self.body.findChildren(EntryRow):
            r.apply_theme(c)

    def show_placeholder(self, text: str = None):
        self.scroll.setVisible(False)
        self.hint.setVisible(True)
        self._last_rendered = None      # 清掉指纹，允许下次重新渲染
        if text:
            self.hint.setText(text)
        self.title.setText("预览")
        self.btn_goto.setEnabled(False)

    # ---- 渲染 ----
    def _clear(self):
        # 先把可能正挂着的 tooltip 收掉：下一步会删掉鼠标底下的控件，
        # 控件一没，Qt 会把气泡窗口跟着销毁/重建，表现为闪一下。
        QToolTip.hideText()
        while self.body_layout.count():
            it = self.body_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _row(self, text: str, bold: bool = False, color: str = "#37474F",
             size: int = 12, icon_pm=None):
        lab = QLabel(text)
        if bold:
            f = lab.font()
            f.setBold(True)
            lab.setFont(f)
        lab.setStyleSheet(
            f"background:transparent;color:{color};font-size:{size}px;")
        lab.setWordWrap(True)
        self.body_layout.addWidget(lab)
        return lab

    def _divider(self):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background:#E8E8E8;border:none;")
        self.body_layout.addWidget(line)

    def _entry_row(self, icon: QPixmap, text: str, tail: str = "",
                   color: str = "#546E7A", size: int = 11,
                   indent: int = 0, tooltip: str = "", path: str = "",
                   is_dir: bool = False):
        """预览面板里的一行：图标 + 名称 + 右侧附加信息。整行可点。"""
        row = EntryRow(icon, text, tail=tail, color=color, size=size,
                       tooltip=tooltip, path=path, is_dir=is_dir)
        if path:
            row.doubleClicked.connect(self._on_entry_double_clicked)
            row.clicked.connect(self._on_entry_selected)
        self.body_layout.addWidget(row)
        return row

    def _finish_loading(self):
        """
        整组条目渲染完毕，统一解除加载态并补上 tooltip。

        批量期间先用 begin/end_tip_batch 压住 tooltip 下发：否则鼠标
        恰好悬在某个条目上时，几十次 setToolTip 会让 Qt 反复重建 tooltip
        窗口，屏幕上就是一串一闪而过的小黑窗。整批结束后只落地一次。
        """
        EntryRow.begin_tip_batch()
        try:
            rows = self.body.findChildren(EntryRow)
            for r in rows:
                r.set_loading(False)
        finally:
            EntryRow.end_tip_batch()
        # 整批结束，一次性生效
        for r in self.body.findChildren(EntryRow):
            r.flush_tooltip()

    def _on_entry_selected(self, path: str):
        """单击只选中：同组内取消其它行，保证同时只有一行高亮。"""
        for r in self.body.findChildren(EntryRow):
            r.set_selected(r.path == path)

    def _on_entry_double_clicked(self, path: str):
        """双击打开：目录进入，文件用系统默认程序打开。"""
        if os.path.isdir(path):
            self._open_requested.emit(path)
        else:
            open_in_explorer(path)

    def show_folder(self, path: str, info):
        """渲染文件夹预览。"""
        self._clear()
        self.path = path
        self.hint.setVisible(False)
        self.scroll.setVisible(True)
        self.btn_goto.setEnabled(True)

        name = os.path.basename(path.rstrip("\\/")) or path
        self.title.setText(f"预览 · {name}"[:30])
        self._row(name, bold=True, size=13)

        if info.error:
            self._row(f"无法读取\n{info.error}", color="#EF5350")
            return

        # 概要
        self._row(f"{info.dir_count} 个文件夹")
        self._row(f"{info.file_count} 个文件")
        self._row(f"本层大小 {human_size(info.total_size)}")
        if info.dir_count:
            deep = info.deep_bytes if info.deep_files else 0
            txt = f"含下级共 {info.deep_files:,} 个文件"
            if deep:
                txt += f" · {human_size(deep)}"
            if info.deep_truncated:
                txt += "（统计已截断）"
            self._row(txt, color="#78909C", size=11)

        self._divider()

        # 子文件夹
        if info.dirs:
            self._row("文件夹", bold=True, color="#607D8B", size=11)
            for dname, dpath in info.dirs[:30]:
                self._entry_row(
                    _small_icon(dpath, True), dname,
                    color="#1565C0", size=12,
                    tooltip=dpath, path=dpath, is_dir=True)   # 点击进入该文件夹
            if len(info.dirs) > 30:
                self._row(f"  …… 另有 {len(info.dirs) - 30} 个",
                          color="#B0BEC5", size=11)

        # 文件
        if info.files:
            if info.dirs:
                self._divider()
            self._row("文件", bold=True, color="#607D8B", size=11)
            for fname, size, mt in info.files[:30]:
                full = os.path.join(path, fname)
                self._entry_row(
                    _small_icon(full, False), fname,
                    tail=human_size(size), color="#546E7A", size=11,
                    # 点击用系统默认程序打开
                    tooltip=f"{full}\n{human_size(size)}  "
                            f"{datetime.fromtimestamp(mt):%Y-%m-%d %H:%M}",
                    path=full, is_dir=False)
            if len(info.files) > 30:
                self._row(f"  …… 另有 {len(info.files) - 30} 个",
                          color="#B0BEC5", size=11)

        if info.truncated:
            self._row("（内容过多，仅显示部分）", color="#FF7043", size=11)

        if not info.dirs and not info.files:
            self._row("空文件夹", color="#B0BEC5")

        self.body_layout.addStretch()
        # 渲染完成，整组条目解除加载态，这时才允许 tooltip 弹出
        self._finish_loading()

    def show_loading(self, path: str = ""):
        """扫描进行中的占位，避免面板空白让人以为没反应。"""
        self._clear()
        self.path = path
        self.hint.setVisible(False)
        self.scroll.setVisible(True)
        self.title.setText("预览 · 读取中")
        self.btn_goto.setEnabled(False)
        self._row("正在读取…", color="#90A4AE", size=11)

    def show_file(self, path: str):
        """渲染文件信息预览。"""
        self._clear()
        self.path = path
        self.hint.setVisible(False)
        self.scroll.setVisible(True)
        self.btn_goto.setEnabled(False)

        name = os.path.basename(path)
        self.title.setText("预览 · 文件")
        self._row(name, bold=True, size=13)
        self._divider()

        try:
            st = os.stat(path)
        except OSError as e:
            self._row(f"无法读取\n{e}", color="#EF5350")
            return

        self._row(f"类型  {kind_of(name)}文件", color="#607D8B", size=11)
        self._row(f"大小  {human_size(st.st_size)}")
        self._row(f"      {st.st_size:,} 字节", color="#B0BEC5", size=10)
        self._divider()
        self._row("修改  " + datetime.fromtimestamp(st.st_mtime)
                  .strftime("%Y-%m-%d %H:%M"), color="#607D8B", size=11)
        self._row("创建  " + datetime.fromtimestamp(st.st_ctime)
                  .strftime("%Y-%m-%d %H:%M"), color="#607D8B", size=11)
        self.body_layout.addStretch()

    def show_image(self, path: str):
        """图片直接显示缩略图，命中「预览」这个词的最有用场景。"""
        self._clear()
        self.path = path
        self.hint.setVisible(False)
        self.scroll.setVisible(True)
        self.btn_goto.setEnabled(False)

        name = os.path.basename(path)
        self.title.setText("预览 · 图片")

        holder = QLabel()
        holder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = QPixmap(path)
        if pm.isNull():
            holder.setText("无法加载图片")
            holder.setStyleSheet("color:#EF5350;font-size:12px;")
        else:
            # 保持比例缩到面板宽度内
            scaled = pm.scaled(
                210, 210,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            holder.setPixmap(scaled)
        self.body_layout.addWidget(holder)

        self._divider()
        self._row(name, bold=True)
        try:
            st = os.stat(path)
            self._row(f"{human_size(st.st_size)}", color="#607D8B", size=11)
            self._row("  " + datetime.fromtimestamp(st.st_mtime)
                      .strftime("%Y-%m-%d %H:%M"), color="#B0BEC5", size=10)
        except OSError:
            pass
        self.body_layout.addStretch()

    def goto(self):
        """进入当前预览的路径（点标题栏的箭头按钮）。"""
        if self.path:
            self._open_requested.emit(self.path)


# ---------------------------------------------------------------- 导航历史

class NavHistory:
    """前进 / 后退历史栈。"""
    def __init__(self):
        self.stack: list[str] = []
        self.index = -1

    def push(self, path: str):
        if 0 <= self.index < len(self.stack) and self.stack[self.index] == path:
            return
        self.stack = self.stack[:self.index + 1]
        self.stack.append(path)
        self.index = len(self.stack) - 1

    @property
    def can_back(self):
        return self.index > 0

    @property
    def can_forward(self):
        return self.index < len(self.stack) - 1

    def back(self):
        if self.can_back:
            self.index -= 1
            return self.stack[self.index]
        return None

    def forward(self):
        if self.can_forward:
            self.index += 1
            return self.stack[self.index]
        return None


class UsageBar(QWidget):
    """极简容量条：底槽 + 填充，一眼看出用了多少。"""

    def __init__(self, pct: int, parent=None):
        super().__init__(parent)
        self.pct = max(0, min(100, int(pct)))
        self.setFixedHeight(5)
        self.setStyleSheet("background:transparent;")

    def apply_theme(self, c: dict):
        """按主题更新容量条底槽颜色。"""
        self._track = c["bar_bg"]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(getattr(self, "_track", "#E3E7EA")))   # 底槽
        p.drawRoundedRect(0, 0, w, h, r, r)
        if self.pct >= 90:
            fill = QColor("#EF5350")                   # 快满了，红色警示
        elif self.pct >= 75:
            fill = QColor("#FFA726")
        else:
            fill = QColor("#42A5F5")
        fw = max(h, int(w * self.pct / 100))
        p.setBrush(fill)
        p.drawRoundedRect(0, 0, fw, h, r, r)
        p.end()


class DriveItemWidget(QWidget):
    """
    侧栏里的单个分区条目：图标 + 盘符名 + 图形化容量条 + 剩余空间。
    原来是「一行盘符 + 一行容量文字」两条列表项，现在合并成一条。
    """

    def __init__(self, d: DriveInfo, parent=None, compact: bool = False):
        super().__init__(parent)
        self.root = d.root
        # 紧凑模式：用于「位置」组的主目录等，没有容量条，
        # 单行显示即可，省纵向空间
        self.compact = compact

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2 if compact else 4, 8, 2 if compact else 4)
        lay.setSpacing(8)

        icon = QLabel()
        pm = drive_icon_pixmap(d)
        if not pm.isNull():
            icon.setPixmap(pm)
        icon.setFixedSize(18 if compact else 22, 18 if compact else 22)
        icon.setStyleSheet("background:transparent;")
        lay.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)

        mid = QVBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(3)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)

        # name 形如「系统 (C:)」，label 形如「系统」——后者已包含在前者里，
        # 直接再显示一遍就重复了。只在卷标确实是额外信息时才补充。
        label_extra = ""
        if d.label and d.label not in d.name:
            label_extra = d.label

        name = QLabel(d.name)
        name.setStyleSheet(
            "background:transparent;color:#37474F;font-size:13px;")
        name.setSizePolicy(QSizePolicy.Policy.Preferred,
                           QSizePolicy.Policy.Preferred)
        top.addWidget(name, 0)

        if label_extra:
            vol = QLabel(label_extra)
            vol.setStyleSheet(
                "background:transparent;color:#90A4AE;font-size:11px;")
            vol.setSizePolicy(QSizePolicy.Policy.Ignored,
                              QSizePolicy.Policy.Preferred)
            top.addWidget(vol, 1)
        else:
            top.addStretch(1)

        # 紧凑模式不显示容量信息（主目录没有需要关注的剩余空间）
        if d.total > 0 and not compact:
            used_pct = int((d.total - d.free) / d.total * 100)
            # 侧栏宽度有限，这里只放百分比；完整的剩余/总量在 tooltip 里。
            # 容量条已经图形化了，文字不必重复占用横向空间。
            free_t = QLabel(f"{used_pct}%")
            free_t.setStyleSheet(
                "background:transparent;color:#90A4AE;font-size:11px;")
            free_t.setSizePolicy(QSizePolicy.Policy.Fixed,
                                 QSizePolicy.Policy.Preferred)
            top.addWidget(free_t, 0)
            mid.addLayout(top)
            # 容量条铺满整行宽度，与上方文字左对齐
            bar = UsageBar(used_pct)
            bar.setSizePolicy(QSizePolicy.Policy.Expanding,
                              QSizePolicy.Policy.Fixed)
            bar_wrap = QVBoxLayout()
            bar_wrap.setContentsMargins(1, 3, 1, 0)
            bar_wrap.addWidget(bar)
            mid.addLayout(bar_wrap)
        else:
            mid.addLayout(top)

        lay.addLayout(mid, 1)

        # QListWidgetItem 的默认高度按图标算（约 22px），装不下图标 +
        # 两行内容 + 容量条，会把文字裁掉。显式给出足够的高度。
        self.setMinimumHeight(30 if compact else 46)
        self.setSizePolicy(QSizePolicy.Policy.Preferred,
                           QSizePolicy.Policy.Fixed)

        tip = d.root
        if d.fstype:
            tip += f"\n{d.fstype}"
        if d.total:
            tip += (f"\n剩余 {human_size(d.free)} / 共 {human_size(d.total)}"
                    f"  (已用 {int((d.total - d.free) / d.total * 100)}%)")
        self.setToolTip(tip)

        # 记下各控件引用，切换主题时按新配色重刷
        self._l_name = name
        self._l_vol = locals().get("vol")
        self._l_pct = locals().get("free_t")
        self._bar = locals().get("bar")
        self._is_active = False
        self._c = THEMES["light"]

    def apply_theme(self, c: dict):
        """按主题重刷文字与容量条颜色。"""
        self._c = c
        self._l_name.setStyleSheet(
            f"background:transparent;color:{c['fg']};font-size:13px;")
        if self._l_vol is not None:
            self._l_vol.setStyleSheet(
                f"background:transparent;color:{c['muted']};font-size:11px;")
        if self._l_pct is not None:
            self._l_pct.setStyleSheet(
                f"background:transparent;color:{c['muted']};font-size:11px;")
        if self._bar is not None:
            self._bar.apply_theme(c)
            self._bar.update()

    def set_active(self, on: bool):
        """选中时把主文字改为高亮色，在选中底上更清晰。"""
        self._is_active = on
        c = getattr(self, "_c", THEMES["light"])
        self._l_name.setStyleSheet(
            f"background:transparent;color:{c['sel_fg'] if on else c['fg']};"
            f"font-size:13px;")


# ---------------------------------------------------------------- 主窗口

def _arrow_pixmap(kind: str, size: int = 18, color="#546E7A") -> QPixmap:
    """用线条画导航箭头，避免特殊字符在部分字体下缺字。"""
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    c = size / 2.0
    if kind in ("left", "right"):
        d = 1 if kind == "right" else -1
        p.drawLine(int(c - d * 3), int(c - 5), int(c + d * 3), int(c))
        p.drawLine(int(c + d * 3), int(c), int(c - d * 3), int(c + 5))
    elif kind == "up":
        p.drawLine(int(c - 5), int(c + 2), int(c), int(c - 3))
        p.drawLine(int(c), int(c - 3), int(c + 5), int(c + 2))
    elif kind == "down":
        # 之前漏了这个分支，传 "down" 会画出空白图标
        p.drawLine(int(c - 5), int(c - 2), int(c), int(c + 3))
        p.drawLine(int(c), int(c + 3), int(c + 5), int(c - 2))
    elif kind == "refresh":
        r = size * 0.30
        p.drawArc(int(c - r), int(c - r), int(r * 2), int(r * 2),
                  40 * 16, 280 * 16)
        p.drawLine(int(c + r - 1), int(c - r - 3), int(c + r + 2), int(c - r + 1))
    elif kind == "menu":
        for i, dy in enumerate((-5, 0, 5)):
            p.drawLine(int(c - 5), int(c + dy), int(c + 5), int(c + dy))
    elif kind == "sun":
        # 太阳：圆心 + 8 道光芒
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = size * 0.22
        p.drawEllipse(QRectF(c - r, c - r, r * 2, r * 2))
        for k in range(8):
            import math
            ang = k * math.pi / 4
            r1, r2 = size * 0.32, size * 0.46
            p.drawLine(int(c + math.cos(ang) * r1),
                       int(c + math.sin(ang) * r1),
                       int(c + math.cos(ang) * r2),
                       int(c + math.sin(ang) * r2))
    elif kind == "moon":
        # 月牙：画一个圆再用背景色圆"咬"掉一块
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        r = size * 0.40
        p.drawEllipse(QRectF(c - r, c - r, r * 2, r * 2))
        # 用透明背景的圆挖出月牙
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        r2 = size * 0.38
        p.drawEllipse(QRectF(c - r2 + size * 0.22, c - r2 - size * 0.10,
                             r2 * 2, r2 * 2))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    p.end()
    return pm


def _view_pixmap(kind: str, size: int = 18, color="#546E7A") -> QPixmap:
    """三种视图模式的矢量小图标。"""
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.5)
    p.setPen(pen)
    if kind == "grid":
        for gy in range(2):
            for gx in range(2):
                p.drawRect(3 + gx * 6, 3 + gy * 6, 4, 4)
    elif kind == "list":
        for i in range(3):
            y = 4 + i * 4
            p.drawRect(3, y, 2, 2)
            p.drawLine(7, y + 1, size - 3, y + 1)
    else:  # rows：带分隔线
        for i in range(3):
            y = 4 + i * 5
            p.drawLine(3, y + 1, size - 3, y + 1)
    p.end()
    return pm


class Explorer(QMainWindow):
    VIEW_ICON, VIEW_LIST, VIEW_DETAIL = 0, 1, 2

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 720)
        self.setAcceptDrops(True)

        self.cwd = os.path.expanduser("~")
        self.history = NavHistory()
        self.show_hidden = False
        self.show_hidden_ext = {".pyc", ".pyo", ".tmp", ".log"}
        self.view_mode = self.VIEW_ICON
        self.preview_enabled = True
        self.sort_key = "name"
        self.sort_desc = False
        self.clipboard: list[str] = []      # 复制的源路径
        self.cut: set[str] = set()          # 剪切
        self.scan_timer = QTimer(self)
        self.scan_timer.setSingleShot(True)
        self.scan_timer.setInterval(180)
        self.scan_timer.timeout.connect(self.refresh)
        self.pending_path: str | None = None

        self.worker = Worker(self)
        self.worker.delete_sig = Worker.DeleteDone()
        self.worker.copy_sig = Worker.CopyDone()
        self.worker.delete_sig.finished.connect(self._on_delete_one)
        self.worker.delete_sig.failed.connect(self._on_delete_fail)
        self.worker.copy_sig.progress.connect(self._on_copy_progress)
        self.worker.copy_sig.finished.connect(self._on_copy_done)

        self._build_ui()
        self.navigate(os.path.expanduser("~"), push_history=True)
        QTimer.singleShot(60, self._check_empty)

    # ---------------- 界面构建

    def _build_ui(self):
        # 顶栏
        nav = QFrame()
        nav.setFixedHeight(56)
        nav.setStyleSheet("QFrame{background:#FAFAFA;border-bottom:1px solid #E0E0E0;}")
        self._nav_frame = nav            # 主题切换时要重刷
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(10, 8, 10, 8)
        nl.setSpacing(6)

        self.btn_back = self._nav_btn("left", "后退 (Alt+←)", self.go_back)
        self.btn_fwd = self._nav_btn("right", "前进 (Alt+→)", self.go_forward)
        self.btn_up = self._nav_btn("up", "上一级 (Alt+↑)", self.go_up)
        self.btn_refresh = self._nav_btn("refresh", "刷新 (F5)", self.refresh)
        self.btn_sidebar = self._nav_btn("menu", "显示/隐藏侧边栏 (F9)",
                                         self.toggle_sidebar)
        for b in (self.btn_back, self.btn_fwd, self.btn_up, self.btn_refresh):
            nl.addWidget(b)
        # 侧栏开关必须真的加进布局，否则它是个游离控件——
        # 既不显示也点不到，F9 隐藏后就再也回不来了。
        nl.addWidget(self.btn_sidebar)

        # 主题切换：显示当前主题对应的图标（浅色显示月亮，
        # 点它切到夜间；夜间显示太阳，点它切回浅色）
        self.btn_theme = QToolButton()
        self.btn_theme.setFixedSize(26, 22)
        self.btn_theme.clicked.connect(self.toggle_theme)
        nl.addWidget(self.btn_theme)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("输入路径后回车")
        self.path_edit.setMinimumWidth(220)
        self.path_edit.returnPressed.connect(
            lambda: self.navigate(self.path_edit.text().strip()))
        nl.addWidget(self.path_edit, 1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  在当前目录中搜索")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(220)
        self.search.textChanged.connect(self.on_search)
        nl.addWidget(self.search)

        # 视图切换：三种模式一组按钮
        self._view_btns = []
        wrap = QWidget()
        wrap.setFixedSize(108, 36)
        wrap_l = QHBoxLayout(wrap)
        wrap_l.setContentsMargins(2, 1, 2, 1)
        wrap_l.setSpacing(0)
        for mode, tip, ico in ((self.VIEW_ICON, "大图标 (Space 切换)", "grid"),
                               (self.VIEW_LIST, "列表", "list"),
                               (self.VIEW_DETAIL, "详细信息", "rows")):
            b = QToolButton()
            b.setToolTip(tip)
            b.setFixedSize(34, 34)
            b.setIcon(QIcon(_view_pixmap(ico)))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, m=mode: self.set_view(m))
            wrap_l.addWidget(b)
            self._view_btns.append(b)
        nl.addWidget(wrap)

        menu_btn = self._nav_btn("menu", "主菜单", self.show_main_menu)
        nl.addWidget(menu_btn)

        # 面包屑
        crumb = QFrame()
        crumb.setFixedHeight(32)
        crumb.setStyleSheet("QFrame{background:#FFFFFF;border-bottom:1px solid #EEEEEE;}")
        self._crumb_frame = crumb        # 主题切换时要重刷
        cl = QHBoxLayout(crumb)
        cl.setContentsMargins(12, 3, 12, 3)
        self.crumb_layout = QHBoxLayout()
        self.crumb_layout.setSpacing(2)
        cl.addLayout(self.crumb_layout, 1)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color:#78909C;font-size:12px;")
        cl.addWidget(self.status_label)

        # 内容区
        self.stack = QStackedWidget()

        # 图标视图
        self.icon_list = QListWidget()
        self.icon_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.icon_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.icon_list.setMovement(QListWidget.Movement.Static)
        self.icon_list.setIconSize(QSize(48, 48))
        self.icon_list.setGridSize(QSize(112, 124))
        self.icon_list.setWordWrap(True)
        self.icon_list.setSpacing(4)
        self.icon_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.icon_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.icon_list.customContextMenuRequested.connect(self.show_context_menu)
        self.icon_list.itemDoubleClicked.connect(self.on_double_click)
        self.icon_list.itemSelectionChanged.connect(self.update_status)
        self.icon_list.itemSelectionChanged.connect(self._on_selection_preview)
        self.icon_list.setAcceptDrops(True)
        self.icon_list.installEventFilter(self)
        self.icon_list.dragEnterEvent = lambda e: self._drag_enter(e)
        self.icon_list.dropEvent = lambda e: self._drop(e)
        self.stack.addWidget(self.icon_list)

        # 列表视图
        self.list_table = QTableWidget(0, 4)
        self.list_table.setHorizontalHeaderLabels(["名称", "大小", "类型", "修改时间"])
        self.list_table.verticalHeader().setVisible(False)
        self.list_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.list_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in (1, 2, 3):
            self.list_table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents)
        self.list_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_table.customContextMenuRequested.connect(self.show_context_menu)
        self.list_table.cellDoubleClicked.connect(
            lambda r, _: self.on_double_click(self._table_item(r)))
        self.list_table.setSortingEnabled(True)
        self.list_table.setAcceptDrops(True)
        if self.list_table.selectionModel():
            self.list_table.selectionModel().selectionChanged.connect(
                self._on_selection_preview)
        else:
            # 排序会重建 model，延后一点再连
            QTimer.singleShot(0, self._connect_table_selection)
        self.list_table.dragEnterEvent = lambda e: self._drag_enter(e)
        self.list_table.dropEvent = lambda e: self._drop(e)
        self.stack.addWidget(self.list_table)

        self.stack.addWidget(self._empty_page())

        # 进度条（覆盖在底部）
        self.progress = QProgressBar()
        self.progress.setFixedHeight(18)
        self.progress.setVisible(False)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(nav)
        lay.addWidget(crumb)

        # 三栏：驱动器栏 | 内容区 | 预览窗格，分隔条均可拖拽
        self.sidebar = self._build_sidebar()
        self.preview = self._build_preview()
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.stack)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, True)
        self.splitter.setSizes([210, 720, 250])
        self.splitter.setHandleWidth(4)
        # 现在有了父对象，再设可见性就不会弹出游离的顶层小窗了
        self.preview.setVisible(self.preview_enabled)
        lay.addWidget(self.splitter, 1)

        pl = QVBoxLayout()
        pl.setContentsMargins(12, 4, 12, 6)
        pl.addWidget(self.progress)
        lay.addLayout(pl)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        # 恢复上次选的主题（默认浅色）
        self.theme = load_theme()
        self.apply_light_theme()

        # 快捷键
        self._install_shortcuts()

    def _build_preview(self):
        """
        构建右侧预览窗格，并接上后台扫描线程。

        注意：绝不能在 pane 还没有父对象时就 setVisible(True)。
        没有父对象的 widget 是一个独立顶层窗口，此刻显示它会在屏幕上
        弹出一个 ~200x100 的小空窗（标题栏只挂着应用名），直到它被
        塞进 splitter 才"归位"——这就是启动时"一闪而过的小空窗口"。
        可见性挪到 addWidget 之后再设。
        """
        pane = PreviewPane()
        pane._open_requested.connect(self.navigate)
        self._install_preview_worker(pane)
        return pane

    def _install_preview_worker(self, pane):
        """预览扫描放后台线程，点大目录也不会卡住界面。"""
        self.preview_worker = QThread(self)
        self.preview_scanner = _PreviewScanner(self.show_hidden)
        self.preview_scanner.moveToThread(self.preview_worker)
        pane._scanner = self.preview_scanner
        pane._thread = self.preview_worker
        self.preview_scanner.result.connect(self._on_preview_ready)
        self.preview_worker.start()

    def request_preview(self, path: str, force: bool = False):
        """请求预览某个路径（文件夹看内容，文件看信息）。"""
        pane = getattr(self, "preview", None)
        if pane is None or not self.preview_enabled:
            return
        if not path:
            pane.show_placeholder()
            return
        if not os.path.exists(path):
            pane.show_placeholder("该项目已不存在")
            return

        # 同一个路径不重复触发。选中信号与手动调用可能对同一次选中
        # 各调一遍，重复扫描 + 重建 widget 会让 tooltip 之类的
        # 子窗口跟着反复出现。
        if not force and pane.path == path and pane.path:
            return

        if os.path.isdir(path):
            # 立刻记下目标路径：后台回调会用 pane.path 做比对来丢弃过期结果，
            # 若这里不设，show_placeholder 会把 pane.path 留在 None，
            # 导致回调永远被当成"已切换到别处"而丢弃。
            pane.path = path
            pane.show_placeholder("正在读取……")
            pane.title.setText(
                f"预览 · {os.path.basename(path.rstrip(chr(92)) or path)}"[:30])
            self.preview_scanner.set_show_hidden(self.show_hidden)
            # 扫描期间显示占位提示，并等结果回来再解除条目加载态
            pane.show_loading(path)
            self.preview_scanner.request(path)
        else:
            ext = os.path.splitext(path)[1].lower()
            pane.path = path
            if ext in IMAGE_EXTS:
                pane.show_image(path)
            else:
                pane.show_file(path)

    def _on_preview_ready(self, path: str, info):
        """后台扫描完成，回到 UI 线程渲染。"""
        pane = getattr(self, "preview", None)
        if pane is None or not self.preview_enabled:
            return
        if pane.path != path:
            return          # 期间用户又点了别的，丢弃这次结果
        # 内容没变就别重建 widget：重建会让 tooltip 等子窗口
        # 跟着反复出现关闭，看起来像程序在闪
        if pane._last_rendered == (path, info.dir_count, info.file_count,
                                  info.total_size):
            return
        pane._last_rendered = (path, info.dir_count, info.file_count,
                              info.total_size)
        pane.show_folder(path, info)

    def _connect_table_selection(self):
        """表格 model 被排序重建后重新挂信号。"""
        sm = self.list_table.selectionModel()
        if sm:
            try:
                sm.selectionChanged.disconnect(self._on_selection_preview)
            except (RuntimeError, TypeError):
                pass
            sm.selectionChanged.connect(self._on_selection_preview)

    def _on_selection_preview(self, *args):
        """选中项变化时刷新预览面板。"""
        if not self.preview_enabled:
            return
        sel = self.selected_paths()
        if len(sel) == 1:
            self.request_preview(sel[0])
        elif len(sel) > 1:
            self.preview.show_placeholder(
                f"已选中 {len(sel)} 个项目\n仅选中单个文件夹时可预览")
        else:
            self.preview.show_placeholder()

    def toggle_preview(self):
        self.preview_enabled = not self.preview_enabled
        self.preview.setVisible(self.preview_enabled)
        if self.preview_enabled:
            sel = self.selected_paths()
            self.request_preview(sel[0] if sel else self.cwd, force=True)
        else:
            self.preview_scanner.cancel()

    def _build_sidebar(self):
        """左侧栏：常用目录 + 所有磁盘分区。"""
        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setMinimumWidth(150)
        panel.setStyleSheet(
            "QFrame#sidebar{background:#FAFAFA;border-right:1px solid #E0E0E0;}")
        self._sidebar_frame = panel      # 主题切换时要重刷（否则列表底部
                                         # 露出的面板空隙在夜间模式下是白条）

        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 8, 0, 8)
        v.setSpacing(0)

        self.side_list = QListWidget()
        self.side_list.setFrameShape(QFrame.Shape.NoFrame)
        self.side_list.setSpacing(1)
        self.side_list.setUniformItemSizes(False)
        self.side_list.setMouseTracking(True)
        # 记录哪些分组处于收起状态；「位置」默认收起，让侧栏更紧凑
        self._side_collapsed = {"home"}
        self._side_groups = []
        self.side_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.side_list.customContextMenuRequested.connect(
            self._side_context_menu)
        self.side_list.itemClicked.connect(self._side_clicked)
        self.side_list.setStyleSheet(
            "QListWidget{background:transparent;}"
            "QListWidget::item{border-radius:6px;margin:1px 6px;padding:2px;}"
            "QListWidget::item:hover{background:#EEEEEE;}"
            "QListWidget::item:selected{background:#BBDEFB;color:#0D47A1;}")
        v.addWidget(self.side_list, 1)

        # 开关按钮不放这里——侧栏隐藏后按钮也跟着消失，
        # 就再也点不回来了。实际放在工具栏（_build_toolbar）。
        self.side_toggle = None

        self.refresh_drives()
        return panel

    def refresh_drives(self):
        """重新枚举磁盘与快捷目录，保留当前选中项。"""
        if not hasattr(self, "side_list"):
            return
        current = self.cwd
        self.side_list.blockSignals(True)
        self.side_list.clear()
        self._drive_items = []
        self._drive_widgets = []
        self._side_groups = []

        try:
            drives = list_drives()
        except Exception:
            drives = []

        homes = [d for d in drives if d.kind == "home"]
        disks = [d for d in drives if d.kind != "home"]

        def add(d: DriveInfo):
            # 用自定义 widget 把「盘符 + 容量」合并成一条，
            # 容量用图形条表示，不再额外占一行列表项
            is_home = d.kind == "home"
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, d.root)
            # 分区项要放得下 widget（图标 + 两行 + 容量条，46px）；
            # 位置项没有容量条，用矮得多的紧凑样式
            item.setSizeHint(QSize(0, 30 if is_home else 46))
            widget = DriveItemWidget(d, compact=is_home)
            self.side_list.addItem(item)
            self.side_list.setItemWidget(item, widget)
            self._drive_widgets.append((item, widget))
            self._drive_items.append(d)

        def emit(group):
            """按该组的收起状态决定是否真正加入列表。"""
            return group not in self._side_collapsed

        if disks:
            # 盘符在最上（最高频入口），收藏夹紧随其后，位置放最后
            self._side_header("此电脑", group="disk")
            for d in disks:
                if emit("disk"):
                    add(d)

        # 收藏夹
        favs = load_favorites()
        if favs:
            self._side_header("收藏夹", group="fav")
            for p in favs:
                if emit("fav"):
                    self._add_fav_item(p)

        if homes:
            self._side_header("位置", group="home")
            for d in homes:
                if emit("home"):
                    add(d)

        self.side_list.blockSignals(False)
        self._sync_side_selection(current)

    def _side_header(self, text, group=None):
        """
        分组标题。带 group 时可点击展开/收起该组内容。

        收起状态存在 self._side_collapsed 里，重新枚举磁盘后仍保持。
        """
        collapsed = group in self._side_collapsed
        it = QListWidgetItem(text)
        f = it.font()
        f.setPointSizeF(max(7.0, f.pointSizeF() - 1.5))
        f.setBold(True)
        it.setFont(f)
        it.setForeground(QColor("#78909C"))
        it.setData(Qt.ItemDataRole.UserRole, None)      # 不可导航
        it.setData(Qt.ItemDataRole.UserRole + 1, group)  # 存组名
        it.setData(Qt.ItemDataRole.UserRole + 2, collapsed)
        # 箭头提示可展开/收起
        # 箭头：收起状态 -> 向下（提示可展开）；展开状态 -> 向上（提示可收起）
        it.setIcon(QIcon(_arrow_pixmap(
            "down" if collapsed else "up", 12, "#90A4AE")))
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)         # 可点击（但不可选中）
        it.setSizeHint(QSize(0, 22))
        if group:
            self._side_groups.append((group, it))
        self.side_list.addItem(it)
        return it
        return it

    def _sync_side_selection(self, path: str):
        """让侧栏跟随当前目录高亮对应项。"""
        path = os.path.abspath(path)
        best = -1
        best_len = -1
        for i in range(self.side_list.count()):
            it = self.side_list.item(i)
            root = it.data(Qt.ItemDataRole.UserRole)
            if not root:
                continue
            r = os.path.abspath(root)
            if path == r or path.startswith(r.rstrip("\\/") + os.sep):
                # 取最长匹配，避免 / 盘抢了 C:\Users 的高亮
                if len(r) > best_len:
                    best_len, best = len(r), i
        self.side_list.setCurrentRow(best)
        # 自定义 widget 不随列表项自动变色，需手动同步选中态
        for item, widget in getattr(self, "_drive_widgets", []):
            widget.set_active(item is self.side_list.currentItem())

    def _add_fav_item(self, path):
        """侧栏里的一条收藏项。"""
        name = os.path.basename(path.rstrip("\\/")) or path
        it = QListWidgetItem(name)          # 必须带文本，否则只显示图标
        it.setData(Qt.ItemDataRole.UserRole, path)
        it.setToolTip(path)
        it.setIcon(icon_for(path, os.path.isdir(path), 18))
        it.setSizeHint(QSize(0, 26))
        self.side_list.addItem(it)
        return it

    def _toggle_group(self, group):
        """展开/收起侧栏分组，然后重建侧栏。"""
        if not group:
            return
        if group in self._side_collapsed:
            self._side_collapsed.discard(group)
        else:
            self._side_collapsed.add(group)
        self.refresh_drives()

    def _side_clicked(self, item):
        # 分组标题：点击展开/收起
        group = item.data(Qt.ItemDataRole.UserRole + 1)
        if group:
            self._toggle_group(group)
            return
        root = item.data(Qt.ItemDataRole.UserRole)
        if root and os.path.isdir(root):
            self.navigate(root)

    def _side_context_menu(self, pos):
        item = self.side_list.itemAt(pos)
        if not item:
            return
        # 分组标题：给展开/收起菜单
        group = item.data(Qt.ItemDataRole.UserRole + 1)
        if group:
            m = QMenu(self)
            collapsed = group in self._side_collapsed
            m.addAction("展开" if collapsed else "收起",
                        lambda: self._toggle_group(group))
            m.exec(self.cursor().pos())
            return
        root = item.data(Qt.ItemDataRole.UserRole)
        if not root or not os.path.isdir(root):
            return
        m = QMenu(self)
        m.addAction("打开", lambda: self.navigate(root))
        m.addAction("在新窗口打开", lambda: self._open_in_new_window(root))
        # 收藏夹里已有的项给「取消收藏」
        if root in load_favorites():
            m.addAction("从收藏夹移除",
                        lambda: self._remove_favorite(root))
        else:
            m.addAction("加入收藏夹",
                        lambda: self._add_favorite(root))
        m.addAction("复制路径", lambda: self._copy_text(root))
        m.addSeparator()
        m.addAction("在资源管理器中打开", lambda: open_in_explorer(root))
        m.addAction("在此处打开命令行", lambda: open_terminal(root))
        m.addSeparator()
        m.addAction("属性", lambda: PropertiesDialog(root, self).exec())
        m.exec(self.cursor().pos())

    def _add_favorite(self, path):
        if add_favorite(path):
            self.refresh_drives()
            self.statusBar().showMessage(
                f"已收藏：{os.path.basename(path) or path}", 2000)

    def _remove_favorite(self, path):
        if remove_favorite(path):
            self.refresh_drives()
            self.statusBar().showMessage(
                f"已取消收藏：{os.path.basename(path) or path}", 2000)

    def toggle_sidebar(self):
        """
        显示/隐藏侧栏。

        开关按钮放在工具栏（btn_sidebar），侧栏自身内部不再放按钮——
        否则侧栏一隐藏按钮也跟着消失，用户再也点不回来。
        这里只改可见性，绝不禁用按钮。
        """
        sidebar = getattr(self, "sidebar", None)
        if sidebar is None:
            return
        sidebar.setVisible(not sidebar.isVisible())
        # 顺带把预览也收起来？不——预览是独立功能，保持原样。
        # 若侧栏隐藏后 splitter 宽度需要归还，Qt 会自动处理。

    def apply_light_theme(self):
        """应用当前主题（保留旧名以兼容既有调用点）。"""
        self._apply_theme(getattr(self, "theme", "light"))

    def _apply_theme(self, name: str):
        """切换主题并刷新所有内联着色的控件。"""
        self.theme = name if name in THEMES else "light"
        c = THEMES[self.theme]
        self._c = c
        self.setStyleSheet(build_qss(c))
        self._apply_tooltip_style(c)
        self._refresh_theme_icon()
        self._repaint_widgets_for_theme()

    def _apply_tooltip_style(self, c: dict):
        """
        让悬浮提示气泡跟随主题。

        tooltip 是独立的顶层窗口，不是主窗口的子控件，所以
        self.setStyleSheet(build_qss(...)) 里的 QToolTip 规则对它完全不生效
        —— 那行一直是死代码。结果气泡沿用系统原生配色，在深色环境下
        显示为一个小黑块，看起来就像"点一下就闪出来的小黑窗口"。
        只有应用级样式表 / 调色板才能管到它，这里两者都设一遍。
        """
        app = QApplication.instance()
        if app is None:
            return
        try:
            app.setStyleSheet(
                "QToolTip{background:%s;color:%s;border:1px solid %s;"
                "padding:4px 6px;}" % (c["bg"], c["fg"], c["border2"]))
        except Exception:
            pass
        try:
            pal = app.palette()
            pal.setColor(pal.ColorRole.ToolTipBase, QColor(c["bg"]))
            pal.setColor(pal.ColorRole.ToolTipText, QColor(c["fg"]))
            app.setPalette(pal)
        except Exception:
            pass

    def toggle_theme(self):
        """在浅色 / 夜间之间切换，并持久化选择。"""
        new = "dark" if getattr(self, "theme", "light") == "light" else "light"
        self._apply_theme(new)
        save_theme(new)
        self.statusBar().showMessage(
            "已切换到夜间主题" if new == "dark" else "已切换到浅色主题", 1500)

    def _repaint_widgets_for_theme(self):
        """
        刷新内联写死了颜色的控件。

        预览条目、容量条、侧栏分区这几处当初用 setStyleSheet 逐个设色，
        内联样式优先级高于全局 qss，不逐个重刷的话夜间主题下会
        出现深底深字完全看不清。
        """
        c = self._c
        try:
            for r in self.preview.body.findChildren(EntryRow):
                r.apply_theme(c)
            self.preview.apply_theme(c)
            for item, widget in getattr(self, "_drive_widgets", []):
                widget.apply_theme(c)
            self.side_list.setStyleSheet(
                "QListWidget{background:%s;}"
                "QListWidget::item{border-radius:6px;margin:1px 6px;padding:2px;}"
                "QListWidget::item:hover{background:%s;}"
                "QListWidget::item:selected{background:%s;color:%s;}"
                % (c["bg"], c["hover"], c["accent_bg"], c["sel_fg"]))
        except Exception:
            pass
        # 顶栏 / 面包屑条 / 状态标签 / 空目录页当初写死了浅色内联样式，
        # 不重刷的话夜间模式下这些区域仍是白底 —— 界面看起来"花的"
        try:
            self._nav_frame.setStyleSheet(
                "QFrame{background:%s;border-bottom:1px solid %s;}"
                % (c["alt_bg"], c["border2"]))
            self._crumb_frame.setStyleSheet(
                "QFrame{background:%s;border-bottom:1px solid %s;}"
                % (c["bg"], c["grid"]))
            self._sidebar_frame.setStyleSheet(
                "QFrame#sidebar{background:%s;border-right:1px solid %s;}"
                % (c["alt_bg"], c["grid"]))
            self.status_label.setStyleSheet(
                f"color:{c['dim']};font-size:12px;")
            self._empty_widget.setStyleSheet(
                f"QWidget{{background:{c['bg']};}}")
            for lab in self._empty_widget.findChildren(QLabel):
                txt = lab.text()
                if txt == "此文件夹为空":
                    lab.setStyleSheet(f"font-size:16px;color:{c['dim']};")
                elif txt.startswith("把文件拖进来"):
                    lab.setStyleSheet(f"font-size:12px;color:{c['muted']};")
        except Exception:
            pass
        # 面包屑按钮是动态生成的，直接按当前路径重建一次最省事
        try:
            self._update_crumbs()
        except Exception:
            pass
        self._refresh_side_headers()
        self._refresh_preview_text()

    def _refresh_side_headers(self):
        """重刷侧栏分组标题颜色。"""
        c = self._c
        for row in range(self.side_list.count()):
            it = self.side_list.item(row)
            if it.data(Qt.ItemDataRole.UserRole + 1):
                it.setForeground(QColor(c["dim"]))

    def _refresh_preview_text(self):
        """让当前预览内容按新主题重绘一次。"""
        try:
            path = self.preview.path
            if not path:
                return
            self.preview._last_rendered = None      # 绕过去重，强制重绘
            if os.path.isdir(path):
                self.request_preview(path, force=True)
            else:
                ext = os.path.splitext(path)[1].lower()
                if ext in IMAGE_EXTS:
                    self.preview.show_image(path)
                else:
                    self.preview.show_file(path)
        except Exception:
            pass

    def _refresh_theme_icon(self):
        """更新主题按钮的图标与提示。"""
        btn = getattr(self, "btn_theme", None)
        if btn is None:
            return
        dark = getattr(self, "theme", "light") == "dark"
        # 当前是浅色 -> 显示月亮（提示可切到夜间）；反之显示太阳
        kind = "sun" if dark else "moon"
        color = "#FFD54F" if dark else "#78909C"
        btn.setIcon(QIcon(_arrow_pixmap(kind, 17, color)))
        btn.setToolTip("切换到浅色主题" if dark else "切换到夜间主题")

    def _empty_page(self):
        page = QWidget()
        # 底色/文字色跟主题走，_apply_theme 时会重刷（否则夜间模式下
        # 空目录页仍是刺眼的白底）
        c = getattr(self, "_c", THEMES["light"])
        page.setStyleSheet(f"QWidget{{background:{c['bg']};}}")
        l = QVBoxLayout(page)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        big = QLabel("🗂")
        big.setStyleSheet("font-size:56px;background:transparent;")
        l.addWidget(big)
        t = QLabel("此文件夹为空")
        t.setStyleSheet(f"font-size:16px;color:{c['dim']};")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(t)
        s = QLabel("把文件拖进来，或用「新建文件夹」开始")
        s.setStyleSheet(f"font-size:12px;color:{c['muted']};")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(s)
        self._empty_widget = page
        return page

    def _nav_btn(self, kind, tip, slot):
        b = QToolButton()
        b.setIcon(QIcon(_arrow_pixmap(kind)))
        b.setToolTip(tip)
        b.setFixedSize(34, 34)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _install_shortcuts(self):
        def act(seq, slot):
            a = QAction(self)
            a.setShortcut(QKeySequence(seq))
            a.triggered.connect(slot)
            self.addAction(a)
            return a

        act("Alt+Left", self.go_back)
        act("Alt+Right", self.go_forward)
        act("Alt+Up", self.go_up)
        act("F5", self.refresh)
        act("Ctrl+L", lambda: self.path_edit.setFocus())
        act("Ctrl+G", self.dialog_goto)
        act("Ctrl+D", self.dialog_goto)
        act("Ctrl+N", self.action_new_folder)
        act("Ctrl+Shift+N", self.action_new_file)
        act("F2", self.action_rename)
        act("Delete", self.action_delete)
        act("Ctrl+C", self.action_copy)
        act("Ctrl+X", self.action_cut)
        act("Ctrl+V", self.action_paste)
        act("Ctrl+A", self.select_all)
        act("Ctrl+Shift+A", self.action_show_hidden)
        act("Backspace", self.go_up)
        act("Space", self.action_toggle_view)
        act("Alt+Enter", self.action_properties)
        act("F9", self.toggle_sidebar)
        act("Ctrl+R", self.refresh_drives)
        act("F1", self.action_about)
        act("F12", self.toggle_preview)
        act("Ctrl+Alt+T", self.toggle_theme)

    # ---------------- 导航

    def navigate(self, path: str, push_history=True, from_paste=False):
        if not path:
            return
        path = os.path.expandvars(os.path.expanduser(path))
        if not os.path.isabs(path):
            path = os.path.join(self.cwd, path)
        path = os.path.abspath(path)
        if os.path.isfile(path):
            path = os.path.dirname(path)
        if not os.path.isdir(path):
            self.show_message("路径不存在", f"找不到: {path}")
            self.path_edit.setText(self.cwd)
            return

        # 换驱动器时清空剪切/复制状态（源不可见）
        if os.path.splitdrive(path)[0].lower() != os.path.splitdrive(self.cwd)[0].lower():
            self.cut.clear()

        self.cwd = path
        if push_history:
            self.history.push(path)
        self.path_edit.setText(path)
        self.setWindowTitle(f"{os.path.basename(path) or path} — {APP_NAME} {APP_VERSION}")
        self.refresh()

    def refresh(self):
        res = scan_dir(self.cwd, show_hidden=self.show_hidden)
        if res.error:
            self.stack.setCurrentWidget(self._empty_widget)
            self.status_label.setText(res.error)
            self._sync_side_selection(self.cwd)
            return
        self._render(res)
        self._update_crumbs()
        self._update_nav_buttons()
        self._sync_side_selection(self.cwd)
        self.path_edit.setText(self.cwd)
        if self.preview_enabled:
            # 目录变了，若无选中则回到占位提示
            if not self.selected_paths():
                self.preview.show_placeholder()

    def go_back(self):
        p = self.history.back()
        if p:
            self.navigate(p, push_history=False)

    def go_forward(self):
        p = self.history.forward()
        if p:
            self.navigate(p, push_history=False)

    def go_up(self):
        parent = os.path.dirname(self.cwd.rstrip("/\\"))
        if parent and parent != self.cwd:
            self.navigate(parent)

    def dialog_goto(self):
        dlg = GoToDialog(self.cwd, self)
        if dlg.exec():
            t = dlg.field.text().strip()
            if t:
                self.navigate(t)

    def _update_nav_buttons(self):
        self.btn_back.setEnabled(self.history.can_back)
        self.btn_fwd.setEnabled(self.history.can_forward)
        self.btn_up.setEnabled(os.path.dirname(self.cwd.rstrip("/\\")) != self.cwd)

    # ---------------- 面包屑

    def _update_crumbs(self):
        while self.crumb_layout.count():
            it = self.crumb_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

        parts = self.cwd.replace("/", "\\").split("\\")
        acc = ""
        # 面包屑配色跟主题走（写死浅色的话，夜间模式下这一条会花掉）
        c = getattr(self, "_c", THEMES["light"])
        style_ok = (f"QPushButton{{border:none;background:transparent;"
                    f"color:{c['file_fg']};"
                    f"padding:3px 5px;border-radius:4px;}}"
                    f"QPushButton:hover{{background:{c['hover']};"
                    f"color:{c['accent']};}}")
        if self.cwd.startswith("\\\\"):
            parts = [""] + [p for p in parts if p]
        for i, part in enumerate(parts):
            if i == 0:
                acc = part + ("\\" if part else "")
            else:
                acc = (acc.rstrip("\\") + "\\" + part)
            b = QPushButton(part if part else "此电脑")
            b.setStyleSheet(style_ok)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFlat(True)
            target = acc if acc else os.environ.get("HOMEDRIVE", "C:") + "\\"
            b.clicked.connect(lambda _, p=target: self.navigate(p))
            self.crumb_layout.addWidget(b)
            if i < len(parts) - 1:
                sep = QLabel("\\")
                sep.setStyleSheet(f"color:{c['faint']};")
                self.crumb_layout.addWidget(sep)
        self.crumb_layout.addStretch()

    # ---------------- 渲染

    def _sorted(self, res: DirScan):
        def key_dir(d):
            if self.sort_key == "name":
                return d[0].lower()
            if self.sort_key == "mtime":
                return d[1]
            return d[0].lower()

        def key_file(f):
            if self.sort_key == "name":
                return f[0].lower()
            if self.sort_key == "size":
                return f[2]
            if self.sort_key == "mtime":
                return f[3]
            if self.sort_key == "kind":
                return kind_of(f[0])
            return f[0].lower()

        dirs = sorted(res.dirs, key=key_dir, reverse=self.sort_desc)
        files = sorted(res.files, key=key_file, reverse=self.sort_desc)
        return dirs, files

    def _render(self, res: DirScan):
        # 重绘会把鼠标底下的条目一起销毁，连同它的悬浮气泡。
        # 不先收掉的话，气泡会在点击/切目录的瞬间闪一下（小窗口），
        # 在深色环境下就是一个突兀的小黑块。
        QToolTip.hideText()
        q = self.search.text().strip().lower()
        dirs, files = self._sorted(res)
        if q:
            dirs = [d for d in dirs if q in d[0].lower()]
            files = [f for f in files if q in f[0].lower()]

        total = len(dirs) + len(files)
        if total == 0:
            self.stack.setCurrentWidget(self._empty_widget)
            self.update_status()
            return
        self.stack.setCurrentWidget(
            self.icon_list if self.view_mode == self.VIEW_ICON else self.list_table)

        if self.view_mode == self.VIEW_ICON:
            self.icon_list.clear()
            for name, path in dirs:
                it = QListWidgetItem(icon_for(path, True, 48), name)
                it.setData(Qt.ItemDataRole.UserRole, path)
                it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                # 不再给每个条目挂 tooltip：文件区是最常被鼠标扫过的地方，
                # 气泡一弹一收就是用户看到的那种"小窗口"。路径在地址栏、
                # 预览窗格和状态栏都能看到，这里不必再重复。
                self.icon_list.addItem(it)
            for name, path, size, mt in files:
                it = QListWidgetItem(icon_for(path, False, 48), name)
                it.setData(Qt.ItemDataRole.UserRole, path)
                it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                self.icon_list.addItem(it)
        else:
            self.list_table.setSortingEnabled(False)
            self.list_table.setRowCount(0)
            self.list_table.setRowCount(total)
            row = 0
            for name, path in dirs:
                self._fill_row(row, name, path, 0, "文件夹",
                               datetime.fromtimestamp(os.path.getmtime(path)
                                                      ).strftime("%Y/%m/%d %H:%M"),
                               True)
                row += 1
            for name, path, size, mt in files:
                self._fill_row(row, name, path, size,
                               f"{kind_of(name)}文件",
                               datetime.fromtimestamp(mt).strftime("%Y/%m/%d %H:%M"),
                               False)
                row += 1
            self.list_table.setSortingEnabled(True)
            self.list_table.sortItems(self._col_for_sort())
            self._connect_table_selection()

        size_txt = f"共 {total:,} 个项目"
        if q:
            size_txt += f"（已筛选）"
        elif res.total_size:
            size_txt += f"，{human_size(res.total_size)}"
        if res.truncated:
            size_txt += "  ·  目录过大，仅显示部分内容"
        self.status_label.setText(size_txt)

    def _fill_row(self, row, name, path, size, kind, mtime, is_dir):
        icon = QTableWidgetItem(icon_for(path, is_dir, 32), name)
        icon.setData(Qt.ItemDataRole.UserRole, path)
        icon.setFlags(icon.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_table.setItem(row, 0, icon)
        size_item = QTableWidgetItem("" if is_dir else human_size(size))
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                   | Qt.AlignmentFlag.AlignVCenter)
        self.list_table.setItem(row, 1, size_item)
        self.list_table.setItem(row, 2, QTableWidgetItem(kind))
        self.list_table.setItem(row, 3, QTableWidgetItem(mtime))

    def _col_for_sort(self):
        return {"name": 0, "size": 1, "kind": 2, "mtime": 3}.get(self.sort_key, 0)

    def _table_item(self, row):
        return self.list_table.item(row, 0)

    # ---------------- 视图模式

    def set_view(self, mode: int):
        self.view_mode = mode
        modes = [self.VIEW_ICON, self.VIEW_LIST, self.VIEW_DETAIL]
        for i, b in enumerate(self._view_btns):
            active = (i < len(modes) and modes[i] == mode)
            b.setProperty("active", active)
            b.setStyleSheet(
                "background:#E3F2FD; border-radius:6px;" if active else "")

        self.list_table.setColumnHidden(1, mode != self.VIEW_DETAIL)
        self.list_table.setColumnHidden(2, mode != self.VIEW_DETAIL)
        self.list_table.setColumnHidden(3, mode != self.VIEW_DETAIL)
        if mode == self.VIEW_DETAIL:
            self.list_table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Interactive)
            self.list_table.horizontalHeader().setDefaultSectionSize(280)
        else:
            self.list_table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Stretch)
        self.refresh()

    def nav_parent_view_buttons(self):
        return getattr(self, "_view_btns", [])

    def action_toggle_view(self):
        order = [self.VIEW_ICON, self.VIEW_DETAIL, self.VIEW_LIST]
        i = order.index(self.view_mode) if self.view_mode in order else 0
        self.set_view(order[(i + 1) % len(order)])

    # ---------------- 选择

    def selected_paths(self) -> list[str]:
        if self.view_mode == self.VIEW_ICON:
            out = []
            for it in self.icon_list.selectedItems():
                p = it.data(Qt.ItemDataRole.UserRole)
                if p:
                    out.append(p)
            return out
        out = []
        for idx in self.list_table.selectionModel().selectedRows() if \
                self.list_table.selectionModel() else []:
            it = self.list_table.item(idx.row(), 0)
            if it:
                p = it.data(Qt.ItemDataRole.UserRole)
                if p:
                    out.append(p)
        return out

    def select_all(self):
        if self.view_mode == self.VIEW_ICON:
            self.icon_list.selectAll()
        else:
            self.list_table.selectAll()

    def update_status(self):
        sel = self.selected_paths()
        if sel:
            total = 0
            for p in sel:
                try:
                    if os.path.isfile(p):
                        total += os.path.getsize(p)
                except OSError:
                    pass
            txt = f"已选择 {len(sel)} 个项目"
            if total:
                txt += f"，{human_size(total)}"
            self.status_label.setText(txt)
        else:
            self.refresh_status_only()

    def refresh_status_only(self):
        self.status_label.setText(f"共 {self.icon_list.count() or self.list_table.rowCount():,} 个项目"
                                  if self.stack.currentWidget() is not self._empty_widget
                                  else "此文件夹为空")

    # ---------------- 事件

    def on_double_click(self, item):
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        if os.path.isdir(path):
            self.navigate(path)
        else:
            open_in_explorer(path)

    def on_search(self, text):
        self.refresh()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        self._drop(e)

    def _drag_enter(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def _drop(self, e):
        if not e.mimeData().hasUrls():
            return
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()]
        if not paths:
            return
        e.acceptProposedAction()
        self.copy_paths(paths, self.cwd)

    # ---------------- 动作

    def action_new_folder(self):
        dlg = NewFolderDialog(self)
        if dlg.exec():
            name = dlg.text()
            if not name:
                self.show_message("名称无效", "文件夹名不能为空，也不能包含 \\ / : * ? \" < > |")
                return
            path = unique_name(os.path.join(self.cwd, name))
            try:
                os.mkdir(path)
                self.refresh()
            except OSError as e:
                self.show_message("创建失败", str(e))

    def action_new_file(self):
        dlg = NewFolderDialog(self)
        dlg.setWindowTitle("新建文本文件")
        if dlg.exec():
            name = dlg.text()
            if not name:
                return
            if not os.path.splitext(name)[1]:
                name += ".txt"
            path = unique_name(os.path.join(self.cwd, name))
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("")
                self.refresh()
            except OSError as e:
                self.show_message("创建失败", str(e))

    def action_rename(self):
        sel = self.selected_paths()
        if len(sel) != 1:
            self.show_message("无法重命名", "请选中一个文件或文件夹")
            return
        old = sel[0]
        dlg = RenameDialog(os.path.basename(old), self)
        if not dlg.exec():
            return
        new = dlg.text()
        if not new or new == os.path.basename(old):
            return
        new_path = os.path.join(os.path.dirname(old), new)
        if os.path.exists(new_path):
            self.show_message("重命名失败", "已存在同名项目")
            return
        try:
            os.rename(old, new_path)
            self.refresh()
        except OSError as e:
            self.show_message("重命名失败", str(e))

    def action_delete(self):
        sel = self.selected_paths()
        if not sel:
            return
        self._confirm_delete(sel)

    def _confirm_delete(self, paths):
        names = "\n".join(f"· {os.path.basename(p)}" for p in paths[:8])
        more = f"\n… 另有 {len(paths) - 8} 项" if len(paths) > 8 else ""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("删除")
        box.setText(f"确定要删除这 {len(paths)} 个项目吗？\n\n{names}{more}")
        box.setInformativeText("它们会被移到回收站，可以从回收站还原。")
        trash_btn = box.addButton("移到回收站", QMessageBox.ButtonRole.DestructiveRole)
        del_btn = box.addButton("永久删除", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(trash_btn)
        box.exec()
        clicked = box.clickedButton()
        if clicked is trash_btn:
            self.worker.do_delete(paths, trash=True)
        elif clicked is del_btn:
            self.worker.do_delete(paths, trash=False)
        else:
            return
        self.statusBar().showMessage("正在删除…")

    def action_copy(self):
        sel = self.selected_paths()
        if sel:
            self.clipboard = list(sel)
            self.cut.clear()
            self.statusBar().showMessage(
                f"已复制 {len(sel)} 个项目，按 Ctrl+V 粘贴", 4000)

    def action_cut(self):
        sel = self.selected_paths()
        if sel:
            self.cut = set(sel)
            self.clipboard = []
            self.statusBar().showMessage(
                f"已剪切 {len(sel)} 个项目，按 Ctrl+V 粘贴", 4000)

    def action_paste(self):
        if self.cut:
            self.move_paths(list(self.cut), self.cwd)
        elif self.clipboard:
            self.copy_paths(self.clipboard, self.cwd)

    def action_about(self):
        AboutDialog(self).exec()

    def action_show_hidden(self):
        self.show_hidden = not self.show_hidden
        self.statusBar().showMessage(
            "已显示隐藏项目" if self.show_hidden else "已隐藏隐藏项目", 2500)
        self.refresh()

    def action_properties(self):
        sel = self.selected_paths()
        if len(sel) == 1:
            PropertiesDialog(sel[0], self).exec()
        elif sel:
            total = sum(os.path.getsize(p) for p in sel
                        if os.path.isfile(p) and os.path.exists(p))
            QMessageBox.information(
                self, "属性",
                f"已选择 {len(sel)} 个项目\n合计大小: {human_size(total)}")
        else:
            # 没有选中则看当前目录
            PropertiesDialog(self.cwd, self).exec()

    def show_main_menu(self):
        m = QMenu(self)
        m.addAction("新建文件夹", self.action_new_folder)
        m.addAction("新建文本文件", self.action_new_file)
        m.addSeparator()
        m.addAction("复制", self.action_copy)
        m.addAction("剪切", self.action_cut)
        m.addAction("粘贴", self.action_paste)
        m.addAction("重命名", self.action_rename)
        m.addAction("删除", self.action_delete)
        m.addSeparator()
        m.addAction("转到…", self.dialog_goto)
        m.addAction("在资源管理器中打开", lambda: open_in_explorer(self.cwd))
        m.addAction("在此处打开命令行", lambda: open_terminal(self.cwd))
        m.addAction("刷新", self.refresh)
        m.addSeparator()
        m.addAction("显示隐藏文件" + ("  ✓" if self.show_hidden else ""),
                    self.action_show_hidden)
        m.addAction("预览窗格" + ("  ✓" if self.preview_enabled else ""),
                    self.toggle_preview)
        m.addAction("属性", self.action_properties)
        m.addSeparator()
        m.addAction(f"关于 {APP_NAME}", self.action_about)
        m.addSeparator()
        m.addAction("退出", self.close)
        m.exec(self.cursor().pos())

    def show_context_menu(self, pos):
        if self.view_mode == self.VIEW_ICON:
            item = self.icon_list.itemAt(pos)
            if item and not item.isSelected():
                self.icon_list.clearSelection()
                item.setSelected(True)
            path = item.data(Qt.ItemDataRole.UserRole) if item else None
        else:
            idx = self.list_table.indexAt(pos)
            if idx.isValid() and not self.list_table.selectionModel().isSelected(idx):
                self.list_table.clearSelection()
                self.list_table.selectRow(idx.row())
            path = self._table_item(idx.row()).data(
                Qt.ItemDataRole.UserRole) if idx.isValid() else None

        m = QMenu(self)
        if path:
            m.addAction("打开", lambda: self.on_double_click(
                QListWidgetItem(icon_for(path, os.path.isdir(path)), "")))
            m.addAction("在新窗口打开",
                        lambda: self._open_in_new_window(path))
            m.addSeparator()
            m.addAction("复制", self.action_copy)
            m.addAction("剪切", self.action_cut)
            m.addAction("重命名", self.action_rename)
            m.addAction("删除", self.action_delete)
            m.addSeparator()
            m.addAction("复制路径", lambda: self._copy_text(path))
            # 收藏夹（只对文件夹有意义）
            if os.path.isdir(path):
                if path in load_favorites():
                    m.addAction("从收藏夹移除",
                                lambda: self._remove_favorite(path))
                else:
                    m.addAction("加入收藏夹",
                                lambda: self._add_favorite(path))
            m.addAction("在资源管理器中显示", lambda: self._reveal(path))
            m.addSeparator()
            m.addAction("属性", lambda: PropertiesDialog(path, self).exec())
        else:
            m.addAction("新建文件夹", self.action_new_folder)
            m.addAction("新建文本文件", self.action_new_file)
            m.addSeparator()
            m.addAction("粘贴", self.action_paste)
            m.addAction("选择全部", self.select_all)
            m.addSeparator()
            m.addAction("在资源管理器中打开", lambda: open_in_explorer(self.cwd))
            m.addAction("在此处打开命令行", lambda: open_terminal(self.cwd))
            m.addSeparator()
            m.addAction("刷新", self.refresh)
            m.addAction("显示隐藏文件" + ("  ✓" if self.show_hidden else ""),
                        self.action_show_hidden)
        m.exec(self.cursor().pos())

    def _open_in_new_window(self, path):
        w = Explorer()
        w.navigate(path)
        w.show()

    def _copy_text(self, text):
        QGuiApplication.clipboard().setText(text)
        self.statusBar().showMessage("路径已复制到剪贴板", 2500)

    def _reveal(self, path):
        d = path if os.path.isdir(path) else os.path.dirname(path)
        open_in_explorer(d)

    # ---------------- 后台任务回调

    def _on_delete_one(self, path):
        # 从界面里移除这一项
        if self.view_mode == self.VIEW_ICON:
            for i in range(self.icon_list.count() - 1, -1, -1):
                if self.icon_list.item(i).data(Qt.ItemDataRole.UserRole) == path:
                    self.icon_list.takeItem(i)
        else:
            for r in range(self.list_table.rowCount() - 1, -1, -1):
                it = self.list_table.item(r, 0)
                if it and it.data(Qt.ItemDataRole.UserRole) == path:
                    self.list_table.removeRow(r)
        self.statusBar().showMessage("已删除 1 项", 1200)

    def _on_delete_fail(self, path, reason):
        QMessageBox.warning(self, "删除失败", f"{os.path.basename(path)}\n{reason}")

    def _on_copy_progress(self, done, total, cur):
        if total:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
            self.progress.setVisible(True)
            self.statusBar().showMessage(f"正在复制: {cur}")

    def _on_copy_done(self, ok, bad):
        self.progress.setVisible(False)
        self.cut.clear()
        self.statusBar().showMessage(f"复制完成：成功 {ok} 项，失败 {bad} 项", 5000)
        self.refresh()

    def copy_paths(self, sources, dest):
        if not sources:
            return
        dest = os.path.abspath(dest)
        self.worker.do_copy(list(sources), dest)

    def move_paths(self, sources, dest):
        import shutil
        moved = failed = 0
        for s in sources:
            if os.path.abspath(s) == os.path.abspath(dest):
                continue
            try:
                d = unique_name(os.path.join(dest, os.path.basename(s)))
                shutil.move(s, d)
                moved += 1
            except OSError:
                failed += 1
        self.cut.clear()
        self.statusBar().showMessage(
            f"移动完成：成功 {moved} 项，失败 {failed} 项", 5000)
        self.refresh()

    # ---------------- 杂项

    def show_message(self, title, text):
        QMessageBox.warning(self, title, text)

    def _check_empty(self):
        pass

    def closeEvent(self, event):
        """退出前停掉后台线程，否则进程不会真正结束。"""
        try:
            self.preview_scanner.cancel()
            self.preview_worker.quit()
            self.preview_worker.wait(1500)
        except (AttributeError, RuntimeError):
            pass
        try:
            self.worker.quit()
            self.worker.wait(1500)
        except (AttributeError, RuntimeError):
            pass
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        # 图标视图里按 F2 直接改名
        if obj is self.icon_list and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_F2:
                self.action_rename()
                return True
        return super().eventFilter(obj, event)


# ---------------------------------------------------------------- 入口

def main():
    app = QApplication.instance() or QApplication(sys.argv if False else [])
    app.setApplicationName(APP_NAME)
    w = Explorer()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import sys
    main()