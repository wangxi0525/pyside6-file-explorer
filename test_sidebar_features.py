"""
验证三项改动：
1. 预览扫描期间不弹tooltip（小黑框）
2. 侧栏盘符文字不被裁剪
3. 收藏夹 + 分组收起/展开
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import QApplication

import core
import main_window as mw
from main_window import EntryRow, Explorer

FAILS = []


def check(name, cond, extra=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra if not cond else ''}")
    if not cond:
        FAILS.append(name)


def click_item(side_list, row):
    side_list.setCurrentRow(row)
    side_list.itemClicked.emit(side_list.item(row))
    for _ in range(10):
        QApplication.instance().processEvents()


def main():
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei UI", 9))

    tmp = tempfile.mkdtemp(prefix="feat_")
    sub = os.path.join(tmp, "项目")
    os.makedirs(os.path.join(sub, "深层"))     # 项目/深层
    with open(os.path.join(sub, "readme.md"), "w", encoding="utf-8") as f:
        f.write("x" * 100)

    w = Explorer()
    w.resize(1180, 720)
    w.show()
    w.navigate(tmp)

    print("== 1. 预览加载态不弹 tooltip ==")
    check("有show_loading 方法", hasattr(w.preview, "show_loading"))
    w.preview.show_loading(sub)
    check("加载提示已显示",
          w.preview.scroll.isVisible() and "读取" in w.preview.title.text(),
          w.preview.title.text())
    # 加载态的条目不应有 tooltip
    rows_loading = [r for r in w.preview.body.findChildren(EntryRow)]
    check("加载态无条目 tooltip",
          all(not r.toolTip() for r in rows_loading),
          str([r.toolTip()[:20] for r in rows_loading]))

    # 渲染完成后才补上 tooltip
    from PySide6.QtCore import Qt as _Qt
    for i in range(w.icon_list.count()):
        p = w.icon_list.item(i).data(_Qt.ItemDataRole.UserRole)
        if p and os.path.basename(p) == "项目":
            w.icon_list.setCurrentRow(i)
            break
    # 上面手动调过 show_loading，pane.path 已是 sub，去重会跳过请求——
    # 强制刷新绕过去
    w.request_preview(sub, force=True)
    w.preview._last_rendered = None      # 绕过去重指纹，确保真的渲染
    for _ in range(80):
        app.processEvents()
        w.preview_worker.wait(40)
        if w.preview.body.findChildren(EntryRow):
            break
    rows_done = [r for r in w.preview.body.findChildren(EntryRow) if r.path]
    check("渲染后有条目", len(rows_done) >= 2, str(len(rows_done)))
    check("渲染完成后 tooltip 生效",
          any(r.toolTip() for r in rows_done),
          "全部为空")
    check("_finish_loading 已解除加载态",
          all(not getattr(r, "_loading", False) for r in rows_done))

    print("== 2. 侧栏条目高度 ==")
    from PySide6.QtWidgets import QListWidgetItem as _QI
    disk_items = []
    for i in range(w.side_list.count()):
        it = w.side_list.item(i)
        root = it.data(_Qt.ItemDataRole.UserRole)
        if root and root.rstrip("\\/").upper() in ("C:", "D:", "E:", "F:"):
            disk_items.append(it)
    check("找到侧栏分区条目", len(disk_items) >= 1, str(len(disk_items)))
    if disk_items:
        h = disk_items[0].sizeHint().height()
        check("条目高度足够（>=44）", h >= 44, f"实际 {h}px")
        wdg = w.side_list.itemWidget(disk_items[0])
        if wdg is not None:
            check("widget 最小高度足够", wdg.minimumHeight() >= 44,
                  f"{wdg.minimumHeight()}px")

    print("== 3. 收藏夹 ==")
    check("core 有收藏夹函数", hasattr(core, "load_favorites"))
    # 用独立的 APPDATA 目录避免污染真实配置
    tmp_appdata = tempfile.mkdtemp(prefix="appdata_")
    old_appdata = os.environ.get("APPDATA")
    os.environ["APPDATA"] = tmp_appdata
    try:
        check("初始为空", core.load_favorites() == [])
        check("添加成功", core.add_favorite(sub) is True)
        check("重复添加返回 False", core.add_favorite(sub) is False)
        check("已保存", core.load_favorites() == [os.path.abspath(sub)],
              str(core.load_favorites()))
        check("切换为取消", core.toggle_favorite(sub) is False)
        check("已移除", core.load_favorites() == [])
        check("再切换为收藏", core.toggle_favorite(sub) is True)
        check("已加回", len(core.load_favorites()) == 1)
        # 不存在的路径会被剔除
        core.save_favorites([sub, "Z:\\不存在的盘"])
        check("不存在的路径被剔除", len(core.load_favorites()) == 1,
              str(core.load_favorites()))

        # 侧栏应出现「收藏夹」组
        w.refresh_drives()
        app.processEvents()
        groups = []
        for i in range(w.side_list.count()):
            g = w.side_list.item(i).data(_Qt.ItemDataRole.UserRole + 1)
            if g:
                groups.append(g)
        check("侧栏有收藏夹分组", "fav" in groups, str(groups))
        check("侧栏有磁盘分组", "disk" in groups, str(groups))
        check("侧栏有位置分组", "home" in groups, str(groups))

        print("== 4. 分组收起/展开 ==")
        check("位置默认收起", "home" in w._side_collapsed)
        home_count_before = sum(
            1 for i in range(w.side_list.count())
            if w.side_list.item(i).data(_Qt.ItemDataRole.UserRole + 1) is None
            and not w.side_list.item(i).data(_Qt.ItemDataRole.UserRole))
        # 点击「位置」标题展开
        home_header_row = None
        for i in range(w.side_list.count()):
            if w.side_list.item(i).data(_Qt.ItemDataRole.UserRole + 1) == "home":
                home_header_row = i
                break
        check("找到位置组标题", home_header_row is not None)
        if home_header_row is not None:
            click_item(w.side_list, home_header_row)
            app.processEvents()
            check("点击后展开（不再收起）",
                  "home" not in w._side_collapsed)
            n_items = sum(1 for i in range(w.side_list.count())
                          if w.side_list.item(i).data(_Qt.ItemDataRole.UserRole))
            check("展开后有主目录项", n_items > home_count_before,
                  f"{n_items} vs {home_count_before}")
            # 再点收起
            for i in range(w.side_list.count()):
                if w.side_list.item(i).data(
                        _Qt.ItemDataRole.UserRole + 1) == "home":
                    click_item(w.side_list, i)
                    break
            app.processEvents()
            check("再次点击收起", "home" in w._side_collapsed)

        print("== 5. 箭头方向 ==")
        # 收起时应显示向下（可展开），展开时向上（可收起）
        def arrow_ink(row_idx):
            """
            返回 (不透明像素数, 上半部分像素数)。
            上半部分多= 向上箭头（∧），下半部分多 = 向下箭头（∨），
            据此判断方向，而不只是判断「有没有画出来」。
            """
            from PySide6.QtGui import QImage
            it = w.side_list.item(row_idx)
            ic = it.icon()
            if ic.isNull():
                return 0, 0
            pm = ic.pixmap(12, 12)
            img = pm.toImage().convertToFormat(
                QImage.Format.Format_ARGB32)
            pts = [(x, y) for y in range(img.height())
                   for x in range(img.width())
                   if img.pixelColor(x, y).alpha() > 20]
            half = img.height() / 2
            upper = sum(1 for _, y in pts if y < half)
            return len(pts), upper

        w.refresh_drives()
        app.processEvents()
        # 先收起 home，再看箭头
        if "home" not in w._side_collapsed:
            for i in range(w.side_list.count()):
                if w.side_list.item(i).data(
                        _Qt.ItemDataRole.UserRole + 1) == "home":
                    click_item(w.side_list, i)
                    break
        app.processEvents()
        home_row = next(
            (i for i in range(w.side_list.count())
             if w.side_list.item(i).data(
                 _Qt.ItemDataRole.UserRole + 1) == "home"), None)
        check("找到位置标题", home_row is not None)
        if home_row is not None:
            n_c, up_c = arrow_ink(home_row)
            check("收起状态的箭头已绘制（非空白）", n_c > 0,
                  f"{n_c} 像素")
            # 收起 -> 向下箭头 -> 像素集中在下半部分
            check("收起时箭头朝下（可展开）", up_c * 2 < n_c,
                  f"上半 {up_c} / 总 {n_c}")

        # 展开后再看，箭头应朝上
        if home_row is not None:
            click_item(w.side_list, home_row)
            app.processEvents()
            row2 = next(
                (i for i in range(w.side_list.count())
                 if w.side_list.item(i).data(
                     _Qt.ItemDataRole.UserRole + 1) == "home"), None)
            n_e, up_e = arrow_ink(row2) if row2 is not None else (0, 0)
            check("展开状态的箭头已绘制", n_e > 0, f"{n_e} 像素")
            check("展开时箭头朝上（可收起）", up_e * 2 > n_e,
                  f"上半 {up_e} / 总 {n_e}")

        print("== 6. 收藏项显示名称 ==")
        core.save_favorites([sub])
        w.refresh_drives()
        app.processEvents()
        fav_items = [
            w.side_list.item(i) for i in range(w.side_list.count())
            if w.side_list.item(i).data(
                _Qt.ItemDataRole.UserRole + 1) is None
            and w.side_list.item(i).data(_Qt.ItemDataRole.UserRole) == sub]
        check("收藏项存在", len(fav_items) == 1, str(len(fav_items)))
        if fav_items:
            check("收藏项有文字（非空）", bool(fav_items[0].text().strip()),
                  repr(fav_items[0].text()))
            check("收藏项文字是文件夹名",
                  fav_items[0].text() == "项目",
                  repr(fav_items[0].text()))
            check("收藏项有图标", not fav_items[0].icon().isNull())
        core.save_favorites([])
    finally:
        if old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = old_appdata
        shutil.rmtree(tmp_appdata, ignore_errors=True)
        core.save_favorites([])     # 清理真实收藏夹

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