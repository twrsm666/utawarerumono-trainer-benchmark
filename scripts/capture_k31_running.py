"""Capture real running screenshots for the accepted K3.1 trainer.

Two images are produced:
  k31-running.png    - the trainer window itself, grabbed from the live window
  k31-game-truth.png - the in-game character panel, captured from the running game

Both are read-only: this script never writes to the game process.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

SOURCE = Path(__file__).resolve().parents[1] / "artifacts" / "k31" / "trainer-source"
ASSETS = Path(__file__).resolve().parents[1] / "docs" / "assets"
sys.path.insert(0, str(SOURCE))

from app import STYLE, TrainerWindow  # noqa: E402

user32 = ctypes.WinDLL("user32", use_last_error=True)


def find_game_window() -> int | None:
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if buffer.value == "受讚頌者 虛偽的假面":
                found.append(hwnd)
                return False
        return True

    user32.EnumWindows(callback, 0)
    return found[0] if found else None


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = TrainerWindow()
    window.show()
    QTest.qWait(1200)
    window.lock_timer.stop()
    window.character_list.setCurrentRow(0)
    QTest.qWait(400)

    ASSETS.mkdir(parents=True, exist_ok=True)
    trainer_shot = window.grab()
    ok_trainer = trainer_shot.save(str(ASSETS / "k31-running.png"), "PNG")
    print("trainer", trainer_shot.width(), "x", trainer_shot.height(), ok_trainer)

    game = find_game_window()
    ok_game = False
    if game:
        user32.ShowWindow(game, 3)
        user32.SetForegroundWindow(game)
        QTest.qWait(1200)
        screen = QGuiApplication.primaryScreen()
        full = screen.grabWindow(0)
        panel = full.copy(0, 0, min(1500, full.width()), min(900, full.height()))
        ok_game = panel.save(str(ASSETS / "k31-game-truth.png"), "PNG")
        print("game", hex(game), panel.width(), "x", panel.height(), ok_game)

    print("characters", len(window.pages))
    window.close()
    app.processEvents()
    return 0 if ok_trainer else 1


if __name__ == "__main__":
    raise SystemExit(main())
