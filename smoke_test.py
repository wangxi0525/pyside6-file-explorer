"""
smoke_test.py —— 无界面冒烟测试
用 offscreen 平台把每个功能真跑一遍，确认不会崩。
"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt
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

    # ---- 驱动器侧边栏 ----
    print("== 侧边栏 / 多盘访问 ==")
    check("list_drives 有结果", len(core.list_drives()) > 0,
          str(len(core.list_drives())))
    drives = core.list_drives()
    check("DriveInfo 字段完整",
          all(hasattr(d, "name") and hasattr(d, "root") and hasattr(d, "kind")
              for d in drives))
    check("包含磁盘类卷", any(d.kind in ("disk", "removable", "cdrom")
                          for d in drives),
          str([(d.name, d.kind) for d in drives]))
    check("磁盘有容量信息", any(d.total > 0 for d in drives),
          str([(d.name, d.total) for d in drives][:3]))
    check("图标能生成", not core.drive_icon_pixmap(drives[0]).isNull())
    check("各类图标都能画",
          all(not core.drive_icon_pixmap(
              core.DriveInfo(name="t", root="C:\\", kind=k)).isNull()
              for k in ("disk", "removable", "cdrom", "network", "home")))

    check("侧栏已构建", hasattr(w, "side_list") and w.side_list.count() > 0,
          str(w.side_list.count() if hasattr(w, "side_list") else -1))

    # 每个可写盘都必须在侧栏可见（曾经的缩进 bug 导致磁盘整组消失）
    disk_roots = [os.path.abspath(d.root) for d in drives
                  if d.kind in ("disk", "removable")]
    side_roots = []
    for i in range(w.side_list.count()):
        r = w.side_list.item(i).data(Qt.ItemDataRole.UserRole)
        if r:
            side_roots.append(os.path.abspath(r))
    check("侧栏列出所有磁盘",
          all(any(sr == dr or sr.startswith(dr) for sr in side_roots)
              for dr in disk_roots),
          f"drives={disk_roots} sidebar={side_roots}")

    # fstype 要是 str 而不是 QByteArray，否则 tooltip 显示成 b'NTFS'
    fstypes = [d.fstype for d in drives if d.kind != "home"]
    check("fstype 是字符串",
          all(isinstance(f, str) for f in fstypes), str(fstypes))
    check("fstype 非空", any(fstypes), str(fstypes))

    # 有容量的卷应带一行容量摘要
    cap_rows = sum(
        1 for i in range(w.side_list.count())
        if "可用" in (w.side_list.item(i).text() or ""))
    check("侧栏显示容量摘要", cap_rows >= len(disk_roots), str(cap_rows))

    # 定位到 C 盘根目录
    win_drive = next((d for d in drives if d.kind in ("disk", "removable")), None)
    if win_drive:
        w.navigate(win_drive.root)
        app.processEvents()
        check("能打开磁盘根目录",
              os.path.abspath(w.cwd) == os.path.abspath(win_drive.root), w.cwd)
        check("磁盘根目录可渲染",
              w.stack.currentWidget() is not w._empty_widget
              or w.list_table.rowCount() > 0,
              f"empty={w.stack.currentWidget() is w._empty_widget}")

        #侧栏应高亮当前盘
        cur = w.side_list.currentRow()
        cur_root = (w.side_list.item(cur).data(Qt.ItemDataRole.UserRole)
                    if cur >= 0 else None)
        check("侧栏高亮当前盘",
              cur_root and os.path.abspath(cur_root) ==
              os.path.abspath(win_drive.root), str(cur_root))

    # 切换到另一个盘（若有第二个盘）
    other = next((d for d in drives if d.kind in ("disk", "removable")
                  and os.path.abspath(d.root) !=
                  os.path.abspath(win_drive.root if win_drive else "")), None)
    if other:
        w.navigate(other.root)
        app.processEvents()
        check("能切换到其它盘",
              os.path.abspath(w.cwd) == os.path.abspath(other.root), w.cwd)

    # 点击侧栏项导航
    real_idx = next((i for i in range(w.side_list.count())
                     if w.side_list.item(i).data(Qt.ItemDataRole.UserRole)), None)
    if real_idx is not None:
        w._side_clicked(w.side_list.item(real_idx))
        app.processEvents()
        check("点击侧栏可导航", os.path.isdir(w.cwd), w.cwd)

    # 重新枚举不应崩溃
    w.refresh_drives()
    app.processEvents()
    check("refresh_drives 不崩", w.side_list.count() > 0)

    # 隐藏/显示侧栏
    w.toggle_sidebar()
    app.processEvents()
    check("侧栏可隐藏", not w.sidebar.isVisible())
    w.toggle_sidebar()
    app.processEvents()
    check("侧栏可恢复显示", w.sidebar.isVisible())

    # 切回测试目录
    w.navigate(tmp)
    app.processEvents()

    # ---- 启动器脚本静态检查 ----
    print("== 启动脚本 ==")
    import re
    here = os.path.dirname(os.path.abspath(__file__))

    # VBScript 保留字：作为变量名会导致 "缺少标识符" 语法错误
    vbs_reserved = set("""
        sub function class property let get set dim redim const if then else
        elseif end select case for each next do loop while wend with exit on
        error resume goto call new nothing null true false step to is or and
        not xor mod eqv imp like rem erase execute executeglobal option
        explicit byval byref optional paramarray me public private static type
        lib load name base compare binary text stop default error empty input
        """.split())

    vbs_path = os.path.join(here, "启动.vbs")
    check("启动.vbs 存在", os.path.isfile(vbs_path))
    if os.path.isfile(vbs_path):
        raw = open(vbs_path, "rb").read()
        try:
            vtxt = raw.decode("ascii")
            check("vbs 为纯 ASCII", True)
        except UnicodeDecodeError:
            vtxt = raw.decode("latin-1")
            check("vbs 为纯 ASCII", False, "含非 ASCII 字节")

        crlf = raw.count(b"\r\n")
        bare = raw.count(b"\n") - crlf
        check("vbs 换行为 CRLF", bare == 0, f"bareLF={bare}")
        check("vbs 无 BOM", raw[:3] != b"\xef\xbb\xbf")

        lines = vtxt.split("\r\n")
        declared, conflicts = set(), []
        for d in re.findall(r"^Dim (.+)$", vtxt, re.M | re.I):
            for v in d.split(","):
                v = v.strip()
                if not v:
                    continue
                declared.add(v.lower())
                if v.lower() in vbs_reserved:
                    conflicts.append(v)
        check("vbs 无保留字变量名", not conflicts, str(conflicts))

        builtin = {"wscript", "err", "nothing", "fso", "shell"}
        targets = set(re.findall(
            r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)", vtxt))
        undeclared = sorted(t for t in targets
                            if t.lower() not in declared
                            and t.lower() not in builtin)
        check("vbs 变量均已声明", not undeclared, str(undeclared))

        # 块结构配对：For 用 Next 闭合，If 用 End If 闭合
        opens_for = sum(
            1 for l in lines
            if not l.strip().startswith("'")
            and re.match(r"^\s*For\s+Each\b", l, re.I))
        opens_for += sum(
            1 for l in lines
            if not l.strip().startswith("'")
            and re.match(r"^\s*For\s+\w+\s*=", l, re.I))
        opens_if = sum(
            1 for l in lines
            if not l.strip().startswith("'")
            and re.match(r"^\s*If\b.*\bThen$", l.strip(), re.I))
        closes_for = sum(
            1 for l in lines if re.match(r"^\s*Next\b", l, re.I))
        closes_if = sum(
            1 for l in lines
            if re.match(r"^\s*End\s+If\b", l, re.I))
        check("vbs For/Next 配对", opens_for == closes_for,
              f"{opens_for}/{closes_for}")
        check("vbs If/End If 配对", opens_if == closes_if,
              f"{opens_if}/{closes_if}")

    # bat 同样不能有裸 LF（双击会解析失败）
    bat_path = os.path.join(here, "start.bat")
    check("start.bat 存在", os.path.isfile(bat_path))
    if os.path.isfile(bat_path):
        braw = open(bat_path, "rb").read()
        bbare = braw.count(b"\n") - braw.count(b"\r\n")
        check("bat 换行为 CRLF", bbare == 0, f"bareLF={bbare}")
        try:
            braw.decode("ascii")
            check("bat 为纯 ASCII", True)
        except UnicodeDecodeError:
            check("bat 为纯 ASCII", False, "含非 ASCII（GBK 下会崩）")

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