"""Собирает Windows .ico из img/train_icon.svg."""
from pathlib import Path

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication
from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "img" / "train_icon.svg"
OUT = Path(__file__).resolve().parent / "app.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_png(size: int) -> Image.Image:
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    renderer = QSvgRenderer(str(SVG))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    ptr = image.bits()
    ptr.setsize(image.byteCount())
    raw = bytes(ptr)
    return Image.frombytes("RGBA", (size, size), raw, "raw", "BGRA")


def main() -> None:
    app = QApplication.instance() or QApplication([])
    del app
    if not SVG.is_file():
        raise SystemExit(f"Нет файла иконки: {SVG}")
    frames = [render_png(size) for size in SIZES]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[1:],
    )
    print(f"Иконка записана: {OUT}")


if __name__ == "__main__":
    main()
