"""
main_window.py —— 主窗口与界面逻辑
"""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import (Qt, QDir, QSize, QTimer, QStandardPaths,
                            QPropertyAnimation, QEasingCurve)
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices,
                           QDragEnterEvent, QDropEvent, QGuiApplication,
                           QKeySequence, QIcon, QPainter, QPen, QPixmap)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFileSystemModel, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QPushButton, QSplitter, QStackedWidget, QStatusBar,
    QTableWidget, QTableWidgetItem, QToolBar, QToolButton, QVBoxLayout,
    QWidget, QAbstractItemView as AIV)

from core import (DirScan, DriveInfo, Worker, drive_icon_pixmap,
                  human_size, icon_for, is_hidden, kind_of, list_drives,
                  open_in_explorer, open_terminal, scan_dir, send2trash,
                  unique_name, EXT_COLOR_MAP)

APP_NAME = "Qt 资源管理器"

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
    elif kind == "refresh":
        r = size * 0.30
        p.drawArc(int(c - r), int(c - r), int(r * 2), int(r * 2),
                  40 * 16, 280 * 16)
        p.drawLine(int(c + r - 1), int(c - r - 3), int(c + r + 2), int(c - r + 1))
    elif kind == "menu":
        for i, dy in enumerate((-5, 0, 5)):
            p.drawLine(int(c - 5), int(c + dy), int(c + 5), int(c + dy))
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

        # 左侧驱动器栏 + 右侧内容区，中间可拖拽调节
        self.sidebar = self._build_sidebar()
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)
        self.splitter.setSizes([210, 970])
        self.splitter.setHandleWidth(4)
        lay.addWidget(self.splitter, 1)

        pl = QVBoxLayout()
        pl.setContentsMargins(12, 4, 12, 6)
        pl.addWidget(self.progress)
        lay.addLayout(pl)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.apply_light_theme()

        # 快捷键
        self._install_shortcuts()

    def _build_sidebar(self):
        """左侧栏：常用目录 + 所有磁盘分区。"""
        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setMinimumWidth(150)
        panel.setStyleSheet(
            "QFrame#sidebar{background:#FAFAFA;border-right:1px solid #E0E0E0;}")

        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 8, 0, 8)
        v.setSpacing(0)

        self.side_list = QListWidget()
        self.side_list.setFrameShape(QFrame.Shape.NoFrame)
        self.side_list.setSpacing(1)
        self.side_list.setUniformItemSizes(False)
        self.side_list.setMouseTracking(True)
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

        self.side_toggle = QToolButton()
        self.side_toggle.setIcon(QIcon(_arrow_pixmap("menu", 16, "#78909C")))
        self.side_toggle.setStyleSheet(
            "QToolButton{border:none;background:transparent;color:#78909C;"
            "padding:2px;}")
        self.side_toggle.setToolTip("显示/隐藏侧边栏 (F9)")
        self.side_toggle.setFixedSize(26, 22)
        self.side_toggle.clicked.connect(self.toggle_sidebar)
        v.addWidget(self.side_toggle, 0, Qt.AlignmentFlag.AlignHCenter)

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

        try:
            drives = list_drives()
        except Exception:
            drives = []

        homes = [d for d in drives if d.kind == "home"]
        disks = [d for d in drives if d.kind != "home"]

        def add(d: DriveInfo):
            it = QListWidgetItem(d.name)
            it.setIcon(QIcon(drive_icon_pixmap(d)))
            it.setData(Qt.ItemDataRole.UserRole, d.root)
            tip = d.root
            if d.fstype:
                tip += f"\n{d.fstype}"
            if d.total:
                used = human_size(d.total - d.free)
                tip += (f"\n已用 {used} / 共 {human_size(d.total)}"
                        f"  ({d.free / d.total * 100:.0f}% 可用)")
            it.setToolTip(tip)
            self.side_list.addItem(it)
            self._drive_items.append(d)
            # 有容量的卷在名称后追加一行紧凑的剩余空间，扫一眼就能判断
            if d.total > 0 and d.kind != "home":
                used_pct = int((d.total - d.free) / d.total * 100)
                sub = QListWidgetItem(f"    {human_size(d.free)} 可用 · {used_pct}% 已用")
                sub.setFlags(Qt.ItemFlag.NoItemFlags)
                f = sub.font()
                f.setPointSizeF(max(7.0, f.pointSizeF() - 1.0))
                sub.setFont(f)
                sub.setForeground(QColor("#FF7043" if used_pct >= 90 else "#90A4AE"))
                self.side_list.addItem(sub)

        if homes:
            head = self._side_header("位置")
            for d in homes:
                add(d)
        if disks:
            head = self._side_header("此电脑")
            for d in disks:
                add(d)

        self.side_list.blockSignals(False)
        self._sync_side_selection(current)

    def _side_header(self, text):
        it = QListWidgetItem(text)
        f = it.font()
        f.setPointSizeF(max(7.0, f.pointSizeF() - 1.5))
        f.setBold(True)
        it.setFont(f)
        it.setForeground(QColor("#90A4AE"))
        it.setFlags(Qt.ItemFlag.NoItemFlags)      # 不可选中
        self.side_list.addItem(it)
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

    def _side_clicked(self, item):
        root = item.data(Qt.ItemDataRole.UserRole)
        if root and os.path.isdir(root):
            self.navigate(root)

    def _side_context_menu(self, pos):
        item = self.side_list.itemAt(pos)
        if not item:
            return
        root = item.data(Qt.ItemDataRole.UserRole)
        if not root or not os.path.isdir(root):
            return
        m = QMenu(self)
        m.addAction("打开", lambda: self.navigate(root))
        m.addAction("在新窗口打开", lambda: self._open_in_new_window(root))
        m.addAction("复制路径", lambda: self._copy_text(root))
        m.addSeparator()
        m.addAction("在资源管理器中打开", lambda: open_in_explorer(root))
        m.addAction("在此处打开命令行", lambda: open_terminal(root))
        m.addSeparator()
        m.addAction("属性", lambda: PropertiesDialog(root, self).exec())
        m.exec(self.cursor().pos())

    def toggle_sidebar(self):
        if not hasattr(self, "sidebar"):
            return
        visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not visible)
        if hasattr(self, "side_toggle"):
            self.side_toggle.setEnabled(not visible)

    def apply_light_theme(self):
        """强制浅色外观，不跟随系统深色模式——文件管理器用浅底更易辨识。"""
        qss = """
        QWidget { background:#FFFFFF; color:#37474F; font-size:13px; }
        QListWidget, QTableWidget { background:#FFFFFF; alternate-background-color:#FAFAFA; }
        QListWidget::item { color:#37474F; }
        QListWidget::item:selected, QTableWidget::item:selected {
            background:#BBDEFB; color:#0D47A1; }
        QTableWidget { gridline-color:#EEEEEE; }
        QHeaderView::section {
            background:#FAFAFA; color:#607D8B; padding:6px; border:none;
            border-bottom:1px solid #E0E0E0; border-right:1px solid #F0F0F0; }
        QToolButton { color:#546E7A; background:transparent; border:none;
                      border-radius:6px; font-size:15px; }
        QToolButton:hover { background:#E3F2FD; color:#1565C0; }
        QToolButton:disabled { color:#CFD8DC; }
        QLineEdit { background:#FFFFFF; color:#37474F;
                    border:1px solid #DDE3E9; border-radius:6px; padding:5px 8px; }
        QLineEdit:focus { border:1px solid #64B5F6; }
        QPushButton { background:#FFFFFF; color:#37474F;
                      border:1px solid #DDE3E9; border-radius:6px; padding:6px 12px; }
        QPushButton:hover { background:#F5F7FA; border-color:#BBDEFB; }
        QDialogButtonBox QPushButton { min-width:72px; }
        QMenu { background:#FFFFFF; border:1px solid #E0E0E0; padding:4px; }
        QMenu::item { padding:7px 24px 7px 12px; border-radius:4px; }
        QMenu::item:selected { background:#E3F2FD; color:#1565C0; }
        QMenu::separator { height:1px; background:#EEEEEE; margin:4px 8px; }
        QStatusBar { background:#FAFAFA; color:#78909C; }
        QProgressBar { border:1px solid #E0E0E0; border-radius:4px;
                       background:#FFFFFF; text-align:center; color:#546E7A; }
        QProgressBar::chunk { background:#64B5F6; border-radius:3px; }
        QScrollBar:vertical { background:#FAFAFA; width:10px; margin:0; }
        QScrollBar::handle:vertical { background:#CFD8DC; border-radius:5px; min-height:30px; }
        QScrollBar::handle:vertical:hover { background:#B0BEC5; }
        QScrollBar::add-line, QScrollBar::sub-line { height:0; width:0; }
        QScrollBar:horizontal { background:#FAFAFA; height:10px; }
        QScrollBar::handle:horizontal { background:#CFD8DC; border-radius:5px; min-width:30px; }
        QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
        QLabel { background:transparent; }
        """
        self.setStyleSheet(qss)

    def _empty_page(self):
        page = QWidget()
        page.setStyleSheet("QWidget{background:#FFFFFF;}")
        l = QVBoxLayout(page)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        big = QLabel("🗂")
        big.setStyleSheet("font-size:56px;background:transparent;")
        l.addWidget(big)
        t = QLabel("此文件夹为空")
        t.setStyleSheet("font-size:16px;color:#78909C;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(t)
        s = QLabel("把文件拖进来，或用「新建文件夹」开始")
        s.setStyleSheet("font-size:12px;color:#B0BEC5;")
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
        self.setWindowTitle(f"{os.path.basename(path) or path} — {APP_NAME}")
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
        style_ok = ("QPushButton{border:none;background:transparent;color:#546E7A;"
                    "padding:3px 5px;border-radius:4px;}"
                    "QPushButton:hover{background:#E3F2FD;color:#1565C0;}")
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
                sep.setStyleSheet("color:#CFD8DC;")
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
                it.setToolTip(path)
                self.icon_list.addItem(it)
            for name, path, size, mt in files:
                it = QListWidgetItem(icon_for(path, False, 48), name)
                it.setData(Qt.ItemDataRole.UserRole, path)
                it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                it.setToolTip(f"{path}\n{human_size(size)}")
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
        icon.setToolTip(path)
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
        m.addAction("属性", self.action_properties)
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