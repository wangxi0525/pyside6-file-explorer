"""生成预览窗格的演示截图。"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from main_window import Explorer

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "demo_shot")

TREE = {
    "项目文档": {"设计稿": {}, "产品需求.pdf": 2400, "会议纪要.docx": 1100},
    "设计素材": {"banner.png": 1800, "icon.svg": 300},
    "代码": {"src": {"app.py": 900, "utils": {"helper.py": 420}},
             "main.py": 1500, "README.md": 260},
}


def build_demo():
    shutil.rmtree(DEMO, ignore_errors=True)
    for name, content in TREE.items():
        base = os.path.join(DEMO, name)
        walk(content, base)


def walk(content, base):
    os.makedirs(base, exist_ok=True)
    for k, v in content.items():
        p = os.path.join(base, k)
        if isinstance(v, dict):
            walk(v, p)
        else:
            with open(p, "wb") as f:
                f.write(b"\0" * v)


def main():
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei UI", 9))
    build_demo()

    w = Explorer()
    w.resize(1180, 720)
    w.show()
    w.navigate(DEMO)

    def pick_folder():
        app.processEvents()
        for i in range(w.icon_list.count()):
            p = w.icon_list.item(i).data(Qt.ItemDataRole.UserRole)
            if p and os.path.basename(p) == "代码":
                w.icon_list.setCurrentRow(i)
                return wait_preview()
        print("没找到目标文件夹")
        app.quit()

    def wait_preview():
        app.processEvents()
        if w.preview.hint.isVisible():
            QTimer.singleShot(300, wait_preview)
            return
        w.grab().save(os.path.join(HERE, "shot_preview.png"))
        # 再截未选中时的占位状态
        w.icon_list.clearSelection()
        app.processEvents()
        QTimer.singleShot(300, shot_empty)

    def shot_empty():
        app.processEvents()
        w.grab().save(os.path.join(HERE, "shot_preview_empty.png"))
        app.quit()

    QTimer.singleShot(1200, pick_folder)
    app.exec()
    print("已生成 shot_preview.png 与 shot_preview_empty.png")


if __name__ == "__main__":
    main()