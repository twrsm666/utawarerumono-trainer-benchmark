from __future__ import annotations

import shutil
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
ASSETS = ROOT / "assets"
NAME = "UtawarerumonoTrainer"
DISPLAY_NAME = "传颂之物-虚伪的假面-人物修改器-v1.1"


def create_assets():
    ASSETS.mkdir(exist_ok=True)
    app = QApplication.instance() or QApplication([])
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#913F4B"))
    painter.drawRoundedRect(QRectF(8, 8, 240, 240), 48, 48)
    painter.setBrush(QColor("#7C333D"))
    painter.drawEllipse(QRectF(39, 39, 178, 178))
    painter.setBrush(QColor("#F4EDE2"))
    painter.drawEllipse(QRectF(47, 47, 162, 162))
    painter.setPen(QPen(QColor("#B89659"), 4))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(57, 57, 142, 142))
    font = QFont("Microsoft YaHei UI")
    font.setPixelSize(104)
    font.setWeight(QFont.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#913F4B"))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "传")
    painter.end()
    png_path = ASSETS / "trainer.png"
    assert pixmap.save(str(png_path), "PNG")

    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    assert pixmap.save(buffer, "PNG")
    png = bytes(buffer.data())
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22)
    (ASSETS / "trainer.ico").write_bytes(header + entry + png)
    return ASSETS / "trainer.ico"


def version_file() -> Path:
    content = """
VSVersionInfo(
  ffi=FixedFileInfo(filevers=(1, 1, 0, 0), prodvers=(1, 1, 0, 0), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('080404b0', [
      StringStruct('CompanyName', '个人制作'),
      StringStruct('FileDescription', '传颂之物：虚伪的假面 人物属性修改器 v1.1'),
      StringStruct('FileVersion', '1.1.0'),
      StringStruct('InternalName', 'UtawarerumonoTrainer'),
      StringStruct('OriginalFilename', 'UtawarerumonoTrainer.exe'),
      StringStruct('ProductName', '传颂之物：虚伪的假面 人物修改器'),
      StringStruct('ProductVersion', '1.1.0')
    ])]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""
    path = ROOT / "version_info.txt"
    path.write_text(content.strip(), encoding="utf-8")
    return path


def build():
    import PyInstaller.__main__

    icon = create_assets()
    version = version_file()
    args = [
        str(ROOT / "app.py"),
        "--name", NAME,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", str(icon),
        "--version-file", str(version),
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        "--specpath", str(BUILD),
        "--exclude-module", "PySide6.QtNetwork",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtSql",
        "--exclude-module", "PySide6.QtTest",
    ]
    PyInstaller.__main__.run(args)
    built = DIST / f"{NAME}.exe"
    if not built.exists():
        raise RuntimeError("未生成 exe 文件")
    target = DIST / f"{DISPLAY_NAME}.exe"
    shutil.copy2(built, target)
    print(f"BUILD_OK\t{target}\t{target.stat().st_size}")


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"BUILD_FAILED: {exc}", file=sys.stderr)
        raise
