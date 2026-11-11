from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import CharacterPage, TrainerWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = TrainerWindow()
    window.show()
    QTest.qWait(500)
    assert window.game.connected, "自动连接失败"
    window.lock_timer.stop()
    assert len(window.pages) >= 18, f"人物页面不足: {len(window.pages)}"
    assert window.character_list.count() == len(window.pages)
    assert window.character_list.currentRow() == 0

    page = window.pages[0]
    assert isinstance(page, CharacterPage)
    assert len(page.rows) == 13, f"属性行数错误: {len(page.rows)}"
    assert window.stack.currentWidget() is page

    xp_row = page.rows["xp"]
    old_xp = xp_row.spin.value()
    editor = xp_row.spin.lineEdit()
    editor.setFocus()
    editor.selectAll()
    QTest.keyClicks(editor, "300")
    assert xp_row.dirty, "键入后未立即标记为待写入"
    window.refresh_game()
    assert editor.text() == "300", f"刷新覆盖了未确认输入: {editor.text()!r}"
    assert xp_row.current_value() == 300, "未确认输入无法正确提交"
    page.revert_changes()
    assert xp_row.spin.value() == old_xp
    assert not xp_row.dirty

    bp_row = page.rows["bp"]
    bp_row.spin.setValue(min(65535, bp_row.spin.value() + 1))
    page.mark_written({"xp": 123})
    assert not xp_row.dirty, "已写入字段未清除待写入标记"
    assert bp_row.dirty, "未写入字段的标记被错误清除"
    page.revert_changes()
    assert not page.rows["bp"].dirty

    window.character_list.setCurrentRow(1)
    QTest.qWait(30)
    assert window.stack.currentWidget() is window.pages[1]

    window.character_list.setCurrentRow(0)
    QTest.qWait(30)
    preview = ROOT / "preview.png"
    assert window.grab().save(str(preview), "PNG"), "界面截图保存失败"
    window.close()
    print(f"UI_TEST_OK pages={len(window.pages)} fields={len(page.rows)} preview={preview}")


if __name__ == "__main__":
    main()
