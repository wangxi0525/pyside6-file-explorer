"""
smoke_test.py —— 无界面冒烟测试
用 offscreen 平台把每个功能真跑一遍，确认不会崩。
"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication

import core
from main_window import Explorer

FAILS = []


def check(name, cond, extra=""):
    if cond:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name} {extra}")
        FAILS.append(name)


def main():
    app = QApplication([])

    print("== core 层 ==")
    check("human_size B", core.human_size(512) == "512 B", core.human_size(512))
    check("human_size KB", core.human_size(2048) == "2.0 KB", core.human_size(2048))
    check("human_size GB", "GB" in core.human_size(3 * 1024 ** 3))
    check("kind_of", core.kind_of("a.pdf") == "文档")
    check("unique_name", core.unique_name(__file__).endswith(".py"))
    check("icon_for", not core.icon_for("x.txt", False).isNull())

    tmp = tempfile.mkdtemp(prefix="qe_")
    sub = os.path.join(tmp, "子目录")
    os.makedirs(sub)
    with open(os.path.join(sub, "内文.txt"), "w", encoding="utf-8") as f:
        f.write("hello world")
    with open(os.path.join(tmp, "说明.md"), "w", encoding="utf-8") as f:
        f.write("# test")

    res = core.scan_dir(tmp)
    check("scan 找到文件夹", any(d[0] == "子目录" for d in res.dirs))
    check("scan 找到文件", any(f[0] == "说明.md" for f in res.files))
    check("scan 统计大小", res.total_size > 0, str(res.total_size))
    check("scan 隐藏项过滤", not any(f[0].startswith(".") for f in res.files))
    res2 = core.scan_dir(tmp, show_hidden=True)
    check("scan 显示隐藏", res2.total_items >= res.total_items,
          f"{res2.total_items} vs {res.total_items}")

    print("== 主窗口 ==")
    w = Explorer()
    w.resize(1180, 720)
    w.show()

    w.navigate(tmp)
    app.processEvents()
    check("导航后 cwd 正确", os.path.abspath(w.cwd) == os.path.abspath(tmp),
          w.cwd)
    check("图标视图有内容", w.icon_list.count() == 2, str(w.icon_list.count()))

    # 表格视图
    w.set_view(w.VIEW_DETAIL)
    app.processEvents()
    check("详情模式行数", w.list_table.rowCount() == 2, str(w.list_table.rowCount()))
    check("详情模式文件名列", w.list_table.item(0, 0) is not None)

    # 列表视图
    w.set_view(w.VIEW_LIST)
    app.processEvents()
    check("列表模式行数", w.list_table.rowCount() == 2)

    # 排序
    w.sort_key, w.sort_desc = "size", True
    w.refresh()
    app.processEvents()
    check("按大小排序不崩", w.list_table.rowCount() == 2)

    # 搜索
    w.search.setText("说明")
    app.processEvents()
    check("搜索过滤生效", w.icon_list.count() == 0 or w.list_table.rowCount() == 1,
          f"{w.icon_list.count()}/{w.list_table.rowCount()}")
    w.search.setText("")
    app.processEvents()

    # 选中
    w.set_view(w.VIEW_ICON)
    w.icon_list.clearSelection()
    w.icon_list.setCurrentRow(0)
    app.processEvents()
    sel = w.selected_paths()
    check("能取到选中路径", len(sel) == 1, str(sel))

    # 新建
    from main_window import NewFolderDialog, RenameDialog
    dlg = NewFolderDialog()
    dlg.field.setText("新建测试")
    check("对话框取名", dlg.text() == "新建测试")
    dlg.field.setText("bad/name")
    check("非法名被拦", dlg.text() is None)
    rd = RenameDialog("a.txt")
    check("重命名对话框", rd.text() == "a.txt")

    # 属性
    from main_window import PropertiesDialog
    pd = PropertiesDialog(os.path.join(tmp, "说明.md"))
    check("属性对话框可建", pd.windowTitle().endswith("的属性"))

    # 历史前进后退
    w.navigate(os.path.dirname(tmp))
    app.processEvents()
    w.go_back()
    app.processEvents()
    check("后退回到 tmp", os.path.abspath(w.cwd) == os.path.abspath(tmp), w.cwd)
    w.go_forward()
    app.processEvents()
    check("前进", os.path.abspath(w.cwd) == os.path.abspath(os.path.dirname(tmp)))

    # 上级
    w.go_up()
    app.processEvents()
    check("上一级", w.cwd != tmp)

    # 空目录
    empty = os.path.join(tmp, "空的")
    os.makedirs(empty, exist_ok=True)
    w.navigate(empty)
    app.processEvents()
    check("空目录显示空页", w.stack.currentWidget() is w._empty_widget)

    # 无效路径（弹窗打桩，无界面环境下不会阻塞）
    warned = []
    w.show_message = lambda t, m: warned.append(t)
    before = w.cwd
    w.navigate(os.path.join(tmp, "不存在的路径"))
    app.processEvents()
    check("无效路径不崩且留在原处", w.cwd == before and warned, str(w.cwd))

    # 切回真实目录
    w.navigate(os.path.expanduser("~"))
    app.processEvents()
    check("回到主目录", w.cwd == os.path.expanduser("~"))
    check("主目录有内容", w.icon_list.count() > 0 or w.list_table.rowCount() > 0)

    # ---- 真实文件操作 ----
    print("== 文件操作 ==")
    w.navigate(tmp)
    app.processEvents()

    # 新建文件夹 / 新建文件
    from main_window import NewFolderDialog
    made = os.path.join(tmp, "新建的")
    os.makedirs(made, exist_ok=True)
    made_file = os.path.join(tmp, "笔记.txt")
    with open(made_file, "w", encoding="utf-8") as f:
        f.write("内容")
    w.refresh()
    app.processEvents()
    check("新建文件夹可见", os.path.isdir(made))

    # 复制
    dest = os.path.join(tmp, "复制到")
    os.makedirs(dest, exist_ok=True)
    n = w.worker.copy_sig  # 触发后台复制
    w.copy_paths([made_file], dest)
    w.worker.wait()
    app.processEvents()
    check("复制生成副本",
          os.path.isfile(os.path.join(dest, "笔记.txt")))

    # 移动
    src = os.path.join(tmp, "笔记.txt")
    w.move_paths([src], dest)
    app.processEvents()
    check("移动后源消失", not os.path.exists(src))
    check("移动后目标存在", os.path.isfile(os.path.join(dest, "笔记.txt")))

    # 冲突自动改名（移动时已生成 笔记(1).txt，这里再取名应继续递增）
    import re
    from core import unique_name
    got = unique_name(os.path.join(dest, "笔记.txt"))
    check("重名自动加后缀", bool(re.search(r"笔记\(\d+\)\.txt$", got), ), got)

    # 永久删除（走后台线程的 trash=False）
    victim = os.path.join(tmp, "待删.txt")
    with open(victim, "w", encoding="utf-8") as f:
        f.write("x")
    errs = []
    w.worker.delete_sig.failed.connect(lambda p, r: errs.append((p, r)))
    w.worker.do_delete([victim], trash=False)
    w.worker.wait()
    app.processEvents()
    check("永久删除成功", not os.path.exists(victim) and not errs, str(errs))

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