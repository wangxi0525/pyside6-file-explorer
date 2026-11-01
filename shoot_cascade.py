"""生成级联视图的演示截图。"""
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
    # 用项目目录本身做示例：子文件夹够多，级联展开两三层看得清
    w.navigate(HERE)
    if "--dark" in sys.argv:
        w._apply_theme("dark")
    else:
        w._apply_theme("light")
    w.set_view(Explorer.VIEW_CASCADE)

    def step():
        # 在级联里点开两层，展示多列效果；优先挑非空文件夹，空列不好看
        def first_nonempty(col):
            for i in range(col.count()):
                it = col.item(i)
                p = it.data(0x0100)
                if it.data(0x0101) and p:
                    try:
                        if os.listdir(p):
                            return it
                    except OSError:
                        pass
            return None

        try:
            col = w.cascade._cols[0]
            it = first_nonempty(col)
            if it is not None:
                w.cascade._on_click(col, it)
                app.processEvents()
            if len(w.cascade._cols) >= 2:
                it2 = first_nonempty(w.cascade._cols[1])
                if it2 is not None:
                    w.cascade._on_click(w.cascade._cols[1], it2)
                    app.processEvents()
        except Exception as e:
            print("展开出错:", e)
        QTimer.singleShot(600, shot)

    def shot():
        w.grab().save(os.path.join(HERE, "shot_cascade.png"))
        print("已生成 shot_cascade.png, 列数 =", len(w.cascade._cols))
        app.quit()

    QTimer.singleShot(1200, step)
    app.exec()


if __name__ == "__main__":
    main()
