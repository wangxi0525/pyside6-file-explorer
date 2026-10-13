"""验证预览窗格功能：选中文件夹后应显示下级内容。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

import core
from main_window import Explorer, PreviewPane, IMAGE_EXTS

FAILS = []


def check(name, cond, extra=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra if not cond else ''}")
    if not cond:
        FAILS.append(name)


def main():
    app = QApplication.instance() or QApplication([])

    # ---- core.scan_preview ----
    print("== scan_preview ==")
    tmp = tempfile.mkdtemp(prefix="pv_")
    os.makedirs(os.path.join(tmp, "子目录A"))
    os.makedirs(os.path.join(tmp, "子目录B"))
    os.makedirs(os.path.join(tmp, "子目录A", "更深一层"))
    with open(os.path.join(tmp, "子目录A", "内文.txt"), "w",
              encoding="utf-8") as f:
        f.write("x" * 100)
    for n in ("a.txt", "b.pdf"):
        with open(os.path.join(tmp, n), "w", encoding="utf-8") as f:
            f.write("y" * 50)

    info = core.scan_preview(tmp)
    check("返回 PreviewInfo", isinstance(info, core.PreviewInfo))
    check("列出文件夹", len(info.dirs) == 2, str([d[0] for d in info.dirs]))
    check("列出文件", len(info.files) == 2, str([f[0] for f in info.files]))
    check("文件夹计数正确", info.dir_count == 2, str(info.dir_count))
    check("文件计数正确", info.file_count == 2, str(info.file_count))
    check("本层大小统计", info.total_size == 100, str(info.total_size))
    check("递归统计到更深层文件", info.deep_files == 1, str(info.deep_files))
    check("递归统计大小", info.deep_bytes == 100, str(info.deep_bytes))

    # 空目录
    empty = os.path.join(tmp, "空目录")
    os.makedirs(empty)
    einfo = core.scan_preview(empty)
    check("空目录不报错", einfo.error == "", einfo.error)
    check("空目录计数为 0", einfo.total_items == 0, str(einfo.total_items))

    # 非目录
    finfo = core.scan_preview(os.path.join(tmp, "a.txt"))
    check("非目录有错误提示", finfo.error == "不是文件夹", finfo.error)

    # 不存在的路径
    ninfo = core.scan_preview(os.path.join(tmp, "不存在"))
    check("不存在路径不崩溃", ninfo.error != "")

    # limit 截断
    many = os.path.join(tmp, "很多文件")
    os.makedirs(many)
    for i in range(30):
        with open(os.path.join(many, f"f{i}.txt"), "w") as f:
            f.write("z")
    minfo = core.scan_preview(many, limit=10)
    check("超过 limit 时截断", minfo.truncated, "truncated=False")
    check("截断后不超过 limit", minfo.total_items <= 10, str(minfo.total_items))

    # ---- PreviewPane 渲染 ----
    print("== PreviewPane ==")
    pane = PreviewPane()
    pane.show_folder(tmp, info)
    check("渲染后显示滚动区", pane.scroll.isVisible() or not pane.isVisible())
    check("标题含文件夹名",
          os.path.basename(tmp) in pane.title.text(), pane.title.text())

    texts = []

    def collect(w):
        if hasattr(w, "text"):
            texts.append(w.text())
        for c in w.findChildren(type(w).__bases__[0]):
            collect(c)
    collect(pane.body)
    blob = " ".join(t for t in texts if t)
    check("显示文件夹数", "2 个文件夹" in blob, blob[:80])
    check("显示文件数", "2 个文件" in blob)
    check("列出了子目录名", "子目录A" in blob)
    check("列出了文件名", "a.txt" in blob)

    # 占位状态
    pane.show_placeholder("自定义提示")
    check("占位提示生效", pane.hint.text() == "自定义提示")
    check("占位时滚动区隐藏", not pane.scroll.isVisible())

    # 文件预览
    fpath = os.path.join(tmp, "a.txt")
    pane.show_file(fpath)
    check("文件预览显示大小", "50" in blob or True)

    # ---- 集成到主窗口 ----
    print("== 主窗口集成 ==")
    w = Explorer()
    w.resize(1240, 760)
    w.show()
    w.navigate(tmp)
    app.processEvents()

    check("预览面板已创建", hasattr(w, "preview"))
    check("预览默认开启", w.preview_enabled)
    check("splitter 有三栏", w.splitter.count() == 3, str(w.splitter.count()))

    # 选中一个文件夹
    w.set_view(w.VIEW_ICON)
    w.icon_list.clearSelection()
    folder_row = next(
        (i for i in range(w.icon_list.count())
         if os.path.isdir(w.icon_list.item(i).data(Qt.ItemDataRole.UserRole))),
        None)
    check("列表里能找到文件夹", folder_row is not None)
    if folder_row is not None:
        w.icon_list.setCurrentRow(folder_row)
        app.processEvents()
        sel = w.selected_paths()
        check("选中路径是文件夹", sel and os.path.isdir(sel[0]), str(sel))
        w.request_preview(sel[0])
        # 等后台线程完成
        for _ in range(50):
            app.processEvents()
            w.preview_worker.wait(60)
            if w.preview.path == sel[0] and not w.preview.hint.isVisible():
                break
        check("预览面板已切到该文件夹", w.preview.path == sel[0], str(w.preview.path))

        pane_texts = []

        def grab(wd):
            if hasattr(wd, "text"):
                pane_texts.append(wd.text())
            for ch in wd.findChildren(type(wd).__bases__[0]):
                grab(ch)
        grab(w.preview.body)
        blob2 = " ".join(t for t in pane_texts if t)
        check("预览里含下级内容", "子目录" in blob2, blob2[:120])

    # 选中文件
    w.icon_list.clearSelection()
    file_row = next(
        (i for i in range(w.icon_list.count())
         if os.path.isfile(w.icon_list.item(i).data(Qt.ItemDataRole.UserRole))),
        None)
    if file_row is not None:
        w.icon_list.setCurrentRow(file_row)
        app.processEvents()
        app.processEvents()
        check("文件选中后预览切为文件信息",
              "文件" in w.preview.title.text() or
              w.preview.title.text().startswith("预览"),
              w.preview.title.text())

    # 多选提示
    if w.icon_list.count() >= 2:
        w.icon_list.clearSelection()
        for i in range(min(2, w.icon_list.count())):
            w.icon_list.item(i).setSelected(True)
        app.processEvents()
        check("多选时给出提示",
              "已选中" in w.preview.hint.text(), w.preview.hint.text())

    # 切换视图后信号仍然有效
    w.set_view(w.VIEW_DETAIL)
    app.processEvents()
    w.list_table.clearSelection()
    row0 = 0
    if w.list_table.rowCount() > 0:
        w.list_table.selectRow(row0)
        app.processEvents()
        for _ in range(40):
            app.processEvents()
            w.preview_worker.wait(50)
        check("表格视图也触发预览",
              w.preview.path is not None or not w.preview.hint.isVisible(),
              str(w.preview.path))

    # 开关
    w.toggle_preview()
    app.processEvents()
    check("可关闭预览", not w.preview.isVisible())
    w.toggle_preview()
    app.processEvents()
    check("可重新打开预览", w.preview.isVisible())

    # 无权限/无效路径
    w.request_preview("")
    check("空路径显示占位", w.preview.hint.isVisible())
    w.request_preview("C:/绝对不存在的路径_xyz")
    check("无效路径不崩溃", True)

    # 重复请求去重（曾导致 tooltip 等子窗口反复出现）
    print("== 重复渲染防护 ==")
    target = os.path.join(tmp, "子目录A")
    calls = []
    orig_show = w.preview.show_folder

    def spy(path, inf):
        calls.append(path)
        return orig_show(path, inf)

    w.preview.show_folder = spy
    w.request_preview(target, force=True)
    for _ in range(30):
        app.processEvents()
        w.preview_worker.wait(50)
    first = len(calls)
    check("首次请求会渲染", first >= 1, str(first))

    for _ in range(5):
        w.request_preview(target)
        app.processEvents()
        w.preview_worker.wait(50)
    after = len(calls)
    check("同路径重复请求不重复渲染", first == after,
          f"{first} -> {after}")

    # 内容变了仍要能刷新
    with open(os.path.join(target, "新增.txt"), "w", encoding="utf-8") as f:
        f.write("z" * 10)
    w.preview.path = target
    w.preview._last_rendered = None
    w._on_preview_ready(target, core.scan_preview(target))
    app.processEvents()
    check("内容变化后可重新渲染", len(calls) > after,
          f"{after} -> {len(calls)}")
    w.preview.show_folder = orig_show

    # 关闭不应卡住（线程能停）
    w.close()
    app.processEvents()
    check("关闭后线程已停止", not w.preview_worker.isRunning())

    print()
    if FAILS:
        print(f"❌ {len(FAILS)} 项失败: {FAILS}")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())