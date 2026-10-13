"""生成侧栏顺序的演示截图。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from main_window import Explorer

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei UI", 9))

    w = Explorer()
    w.resize(1240, 760)
    w.show()
    w.navigate("C:\\")

    def shot():
        w.grab().save(os.path.join(HERE, "shot_sidebar.png"))
        app.quit()

    QTimer.singleShot(1400, shot)
    app.exec()
    print("已生成 shot_sidebar.png")


if __name__ == "__main__":
    main()