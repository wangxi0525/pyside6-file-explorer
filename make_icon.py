"""
make_icon.py —— 生成应用图标 app_icon.ico

用 QPainter 画一个「文件夹 + 放大镜」图形，导出多尺寸 ico。
不依赖任何外部图片素材。手工拼 ICO 容器以支持多分辨率。
"""
import os
import struct
import sys

from PySide6.QtCore import Qt, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(size: int) -> QPixmap:
    """按 256 为设计基准等比绘制图标。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    s = size / 256.0

    def px(v):
        return int(round(v * s))

    # 文件夹：后标签 -> 前标签 -> 主体
    p.setPen(QPen(QColor("#E08600"), max(1.0, px(4))))
    p.setBrush(QColor("#FFB300"))
    p.drawRoundedRect(px(28), px(64), px(200), px(150), px(18), px(18))

    p.setBrush(QColor("#FFC94D"))
    p.drawRoundedRect(px(18), px(46), px(110), px(36), px(14), px(14))

    p.setBrush(QColor("#FFE082"))
    p.drawRoundedRect(px(18), px(96), px(220), px(120), px(18), px(18))

    # 放大镜
    cx, cy, r = px(150), px(150), px(58)
    p.setBrush(QColor(29, 116, 200, 190))
    p.setPen(QPen(QColor("#0D47A1"), max(1.0, px(12))))
    p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    p.setPen(QPen(QColor("#0D47A1"), max(2.0, px(20)),
                  Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(int(cx + r * 0.62), int(cy + r * 0.62),
               int(cx + r * 1.30), int(cy + r * 1.30))

    # 高光
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 110))
    p.drawEllipse(int(cx - r * 0.55), int(cy - r * 0.62),
                  int(r * 0.75), int(r * 0.48))

    p.end()
    return pm


def png_bytes(pm: QPixmap) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pm.save(buf, "PNG")
    buf.close()
    return bytes(ba)


def write_ico(path: str) -> bool:
    """
    手工拼 ICO：ICONDIR(6B) + ICONDIRENTRY(16B * n) + 各图 PNG 数据。
    Vista 之后允许在 ICO 内直接内嵌 PNG。
    """
    images = [(s, png_bytes(render(s))) for s in SIZES]

    offset = 6 + 16 * len(images)
    entries = b""
    for size, data in images:
        # 256 在 ICONDIR 里记为 0
        w = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32,
                               len(data), offset)
        offset += len(data)

    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(images)))
        f.write(entries)
        for _, data in images:
            f.write(data)
    return True


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "app_icon.ico")
    if os.path.exists(out):
        os.remove(out)

    try:
        write_ico(out)
    except Exception as e:
        print(f"生成失败: {e}")
        return 1

    size_kb = os.path.getsize(out) / 1024
    print(f"已生成 {out}  ({size_kb:.1f} KB)")
    print(f"内含尺寸: {SIZES}")

    # 额外导出一张 256 png，便于 README 展示
    png = os.path.join(os.path.dirname(out), "app_icon.png")
    render(256).save(png, "PNG")
    print(f"已生成 {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())