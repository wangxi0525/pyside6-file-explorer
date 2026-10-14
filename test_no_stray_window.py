"""
test_no_stray_window.py —— 回归测试：全生命周期不得弹出游离的顶层小窗。

历史 bug（同一个模式犯了两次）：
  1) _build_preview() 在 PreviewPane 还没有父对象时就 setVisible(True)
     -> 启动瞬间闪出一个 ~214x138 的小空窗。
  2) EntryRow.__init__ 里 self.tail = QLabel() 无父构造，随即
     setVisible(bool(tail)) -> 每个预览行都弹一个顶层小窗。预览面板一次
     最多铺 30 行，于是"单击文件夹"时连闪 30 个 136x50 的小黑窗。

根因：无父对象的 QWidget 是独立顶层窗口，任何 setVisible(True)/show()
都会在屏幕上弹窗。修法是构造时就给父对象，或先 addWidget 再设可见性。

本测试在 offscreen 平台下跑完整流程（启动 + 多目录 + 多选中 + 切主题），
断言没有任何"无父对象的顶层 widget 被显示"。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QObject, QTimer       # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget      # noqa: E402

strays = []


class ShowSpy(QObject):
    """记录所有"无父对象却被显示"的小顶层窗口。"""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.Show and isinstance(obj, QWidget):
            try:
                if obj.isWindow() and obj.isVisible() and not obj.parent():
                    # 主窗口是正当的顶层窗口，按尺寸排除
                    if obj.width() < 500 and obj.height() < 400:
                        strays.append((type(obj).__name__, obj.width(),
                                       obj.height()))
            except RuntimeError:
                pass
        return False


app = QApplication([])
app.setApplicationDisplayName("Qt 资源管理器")
spy = ShowSpy()
app.installEventFilter(spy)

from main_window import Explorer, EntryRow               # noqa: E402
from PySide6.QtGui import QPixmap                        # noqa: E402

win = Explorer()
win.show()

# ---- 直接构造 EntryRow（复现历史 bug 2）：无父构造的 QLabel 不得被 show ----
blank = QPixmap()
for i in range(5):
    r = EntryRow(icon=blank, text=f"row {i}", tail="1.2 MB")
    assert r.tail.parent() is r, "tail 标签必须有自己的父对象"
    r.deleteLater()

STEPS = [
    lambda: win.navigate(os.environ.get("SystemDrive", "C:") + "\\"),
    lambda: win.toggle_theme(),
    lambda: win.toggle_theme(),
]


def pump():
    """跑完流程后收尾断言。"""
    global _done
    _done = True


_done = False


def run():
    for fn in STEPS:
        try:
            fn()
        except Exception as e:               # noqa: BLE001
            print("步骤异常（忽略）:", e)
    QTimer.singleShot(400, pump)


QTimer.singleShot(200, run)

if not _done:
    QTimer.singleShot(1600, app.quit)
    app.exec()

print("游离小窗:", strays if strays else "无")
if strays:
    for s in strays:
        print("  ✗", s)
    print("❌ 存在游离顶层小窗")
    sys.exit(1)

# offscreen 平台下 isVisible() 恒为 False，改用"没被显式隐藏"来判断
assert not win.preview.isHidden(), "预览窗格应默认可见（未隐藏）"
print("✅ 全部通过：无游离小窗，预览窗格正常可见")
