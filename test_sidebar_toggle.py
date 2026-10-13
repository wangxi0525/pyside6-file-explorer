"""
验证侧栏隐藏后可以重新显示（曾因按钮被禁用 + 按钮藏在内侧栏而无法恢复）。

覆盖三种调用方式：
1. 工具栏按钮 btn_sidebar
2. 快捷键 F9（action触发）
3. 直接调 toggle_sidebar
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from main_window import Explorer

FAILS = []


def check(name, cond, extra=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra if not cond else ''}")
    if not cond:
        FAILS.append(name)


def main():
    app = QApplication.instance() or QApplication([])
    w = Explorer()
    w.resize(1180, 720)
    w.show()
    app.processEvents()

    print("== 初始状态 ==")
    check("侧栏可见", w.sidebar.isVisible())
    check("工具栏有侧栏按钮", hasattr(w, "btn_sidebar")
          and w.btn_sidebar is not None)

    print("== 工具栏按钮切换 ==")
    w.btn_sidebar.click()
    app.processEvents()
    check("点击后侧栏隐藏", not w.sidebar.isVisible())
    check("按钮仍可用（关键：不能被禁用）", w.btn_sidebar.isEnabled())
    check("按钮仍在工具栏可见", w.btn_sidebar.isVisible())

    # 再点回来——这就是原来做不到的一步
    w.btn_sidebar.click()
    app.processEvents()
    check("再次点击可恢复显示", w.sidebar.isVisible())
    check("恢复后宽度合理", w.sidebar.width() >= 100,
          str(w.sidebar.width()))

    print("== 快捷键 F9 ==")
    w.btn_sidebar.click()
    app.processEvents()
    check("F9 隐藏后侧栏不可见", not w.sidebar.isVisible())
    # 用 action 触发快捷键
    for act in w.findChildren(type(w.btn_sidebar.defaultAction() or w)):
        pass
    shortcuts = [s.toString() for s in
                 (w.btn_sidebar.shortcut() and [w.btn_sidebar.shortcut()] or [])]
    QTest.keyClick(w, Qt.Key.Key_F9)
    app.processEvents()
    check("F9 能恢复显示", w.sidebar.isVisible(),
          f"shortcut={shortcuts}")

    print("== 直接调方法 ==")
    w.toggle_sidebar()
    app.processEvents()
    check("方法调用可隐藏", not w.sidebar.isVisible())
    w.toggle_sidebar()
    app.processEvents()
    check("方法调用可恢复", w.sidebar.isVisible())

    print("== 多次往返 ==")
    ok = True
    for i in range(5):
        w.toggle_sidebar()
        app.processEvents()
        if w.sidebar.isVisible():
            ok = False
        w.toggle_sidebar()
        app.processEvents()
        if not w.sidebar.isVisible():
            ok = False
    check("连续 5 次往返都正常", ok)

    print("== 侧栏内部不应再有开关按钮 ==")
    # 原 bug 的根源：按钮在侧栏内部，隐藏后就点不到了
    from PySide6.QtWidgets import QToolButton
    inner = [b for b in w.sidebar.findChildren(QToolButton)]
    check("侧栏内无开关按钮", len(inner) == 0,
          f"发现 {len(inner)} 个")

    print("== splitter 尺寸 ==")
    sizes = w.splitter.sizes()
    check("splitter 仍是三栏", len(sizes) == 3, str(sizes))
    check("侧栏占位恢复", sizes[0] > 0, str(sizes))

    w.close()
    app.processEvents()

    print()
    if FAILS:
        print(f"❌ {len(FAILS)} 项失败: {FAILS}")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())