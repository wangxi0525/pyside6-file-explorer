"""check_preview_visible.py —— 确认预览窗格可见性逻辑未被改坏。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication          # noqa: E402

app = QApplication([])
from main_window import Explorer                    # noqa: E402

w = Explorer()
w.show()
r = []
r.append(("预览窗格默认可见", w.preview.isVisible() is True))
w.toggle_preview()
r.append(("F12 切换后隐藏", w.preview.isVisible() is False))
w.toggle_preview()
r.append(("再次切换后恢复", w.preview.isVisible() is True))

ok = True
for name, good in r:
    print(f"  [{'PASS' if good else 'FAIL'}] {name}")
    ok = ok and good
print("全部通过" if ok else "有失败项")
sys.exit(0 if ok else 1)
