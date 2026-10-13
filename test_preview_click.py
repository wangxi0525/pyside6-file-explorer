"""
验证预览窗格里的条目可点击打开：文件夹进入、文件用系统程序打开。

不真的启动外部程序——通过替换 open_in_explorer 捕获调用。
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import QApplication

import main_window as mw
from main_window import EntryRow, Explorer

FAILS = []


def check(name, cond, extra=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra if not cond else ''}")
    if not cond:
        FAILS.append(name)


def click(wdg):
    """模拟单击（左键按下+释放）。"""
    from PySide6.QtCore import Qt as _Qt
    press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5),
                        _Qt.MouseButton.LeftButton, _Qt.MouseButton.LeftButton,
                        _Qt.KeyboardModifier.NoModifier)
    wdg.mousePressEvent(press)


def double_click(wdg):
    """模拟双击（press, release, doubleclick）。"""
    from PySide6.QtCore import Qt as _Qt
    press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5),
                        _Qt.MouseButton.LeftButton, _Qt.MouseButton.LeftButton,
                        _Qt.KeyboardModifier.NoModifier)
    release = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(5, 5),
                          _Qt.MouseButton.LeftButton, _Qt.MouseButton.NoButton,
                          _Qt.KeyboardModifier.NoModifier)
    dbl = QMouseEvent(QEvent.Type.MouseButtonDblClick, QPointF(5, 5),
                      _Qt.MouseButton.LeftButton, _Qt.MouseButton.LeftButton,
                      _Qt.KeyboardModifier.NoModifier)
    wdg.mousePressEvent(press)
    wdg.mouseReleaseEvent(release)
    wdg.mouseDoubleClickEvent(dbl)


def main():
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei UI", 9))

    # 造测试目录：外层含内层，内层里放文件——选中内层才有条目可点
    tmp = tempfile.mkdtemp(prefix="entry_click_")
    sub = os.path.join(tmp, "子目录")
    inner = os.path.join(sub, "更深一层")
    os.makedirs(inner)
    f1 = os.path.join(sub, "a.txt")
    with open(f1, "w", encoding="utf-8") as fh:
        fh.write("x" * 50)

    # 捕获「用系统程序打开」的调用，避免真的启动程序
    opened = []
    orig_open = mw.open_in_explorer
    mw.open_in_explorer = lambda p: opened.append(p)

    navigated = []
    w = Explorer()
    w.resize(1100, 700)
    w.show()
    w.navigate(tmp)
    app.processEvents()
    # _open_requested 在 PreviewPane 上（主窗口在 967 行处 connect 到 navigate）
    w.preview._open_requested.connect(lambda p: navigated.append(p))

    # 选中子目录（预览需要先选中才会渲染）
    from PySide6.QtCore import Qt
    target = None
    for i in range(w.icon_list.count()):
        p = w.icon_list.item(i).data(Qt.ItemDataRole.UserRole)
        if p and os.path.isdir(p):
            target = i
            break
    check("目录列表含子目录", target is not None)
    w.icon_list.setCurrentRow(target)
    # 现在扫描期间会先显示「正在读取」占位，要等实际条目渲染出来
    for _ in range(80):
        app.processEvents()
        w.preview_worker.wait(40)
        if [r for r in w.preview.body.findChildren(EntryRow) if r.path]:
            break

    check("预览已显示", w.preview.scroll.isVisible())

    rows = [r for r in w.preview.body.findChildren(EntryRow)]
    check("条目为 EntryRow", len(rows) >= 2, str(len(rows)))

    dir_rows = [r for r in rows if os.path.isdir(r.path)]
    file_rows = [r for r in rows if r.path and os.path.isfile(r.path)]
    check("找到目录条目", len(dir_rows) == 1, str(len(dir_rows)))
    check("找到文件条目", len(file_rows) == 1, str(len(file_rows)))

    # 单击文件 -> 只选中，不打开（避免误触）
    if file_rows:
        click(file_rows[0])
        app.processEvents()
        check("单击文件不触发打开", opened == [], f"opened={opened}")
        check("单击后该行高亮选中", file_rows[0]._selected)
        if len(file_rows) > 1:
            click(file_rows[1])
            app.processEvents()
            check("改选其它行时原行取消选中",
                  not file_rows[0]._selected and file_rows[1]._selected)
            click(file_rows[0])

    # 单击目录 -> 只选中，不导航
    if dir_rows:
        click(dir_rows[0])
        app.processEvents()
        check("单击目录不触发导航", navigated == [], f"navigated={navigated}")

    # 双击文件 -> 调open_in_explorer
    if file_rows:
        double_click(file_rows[0])
        app.processEvents()
        check("双击文件触发系统打开", opened == [f1],
              f"opened={opened}")

    # 双击目录 -> 导航（预览里显示的是「子目录」的下一级，
    # 即「更深一层」，不是 sub 本身）
    if dir_rows:
        double_click(dir_rows[0])
        app.processEvents()
        check("双击目录触发导航", dir_rows[0].path in navigated,
              f"期望 {dir_rows[0].path}，实际 {navigated}")

    # 悬停样式（先取消选中，避免与选中蓝混淆）
    if file_rows:
        r = file_rows[0]
        r.set_selected(False)
        r.enterEvent(None)
        app.processEvents()
        bg_hover = "E3F2FD" in r.name.styleSheet()
        check("悬停时整行变浅蓝", bg_hover, r.name.styleSheet()[:60])
        r.leaveEvent(None)
        app.processEvents()
        check("移开后恢复透明",
              "transparent" in r.name.styleSheet(),
              r.name.styleSheet()[:60])

    # 选中态应比悬停更深
    if file_rows:
        r = file_rows[0]
        r.set_selected(True)
        app.processEvents()
        check("选中时高亮更深", "BBDEFB" in r.name.styleSheet(),
              r.name.styleSheet()[:60])
        r.set_selected(False)

    # tooltip
    if file_rows:
        check("条目有 tooltip", bool(file_rows[0].toolTip()),
              repr(file_rows[0].toolTip()[:40]))

    # 光标
    if file_rows:
        check("可点条目用手型光标",
              file_rows[0].cursor().shape().name.lower().find("pointing") >= 0,
              file_rows[0].cursor().shape().name)

    mw.open_in_explorer = orig_open
    w.close()
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print(f"❌ {len(FAILS)} 项失败: {FAILS}")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())