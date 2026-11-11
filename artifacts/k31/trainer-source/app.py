from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCloseEvent, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QStackedWidget, QStatusBar, QVBoxLayout, QWidget,
)

from game_memory import (
    CharacterStats, FIELDS, GameMemory, GameNotFoundError, MemoryWriteError,
)

APP_TITLE = "传颂之物：虚伪的假面 · 人物修改器 v1.1"
COLORS = ["#9A4550", "#397B78", "#A66A35", "#626A9A", "#7D5B8E", "#47704E"]

STYLE = """
QMainWindow, QWidget#Root { background: #F5F3EE; color: #263138; }
QWidget { font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif; font-size: 13px; }
QLabel#AppTitle { font-size: 22px; font-weight: 700; color: #263138; }
QLabel#AppSubtitle { color: #788188; font-size: 12px; }
QLabel#CharacterName { font-size: 27px; font-weight: 700; color: #2C343A; }
QLabel#CharacterMeta { color: #7A8388; font-size: 12px; }
QLabel#SectionTitle { font-size: 15px; font-weight: 700; color: #334047; }
QLabel#SummaryValue { font-size: 19px; font-weight: 700; color: #913F4B; }
QLabel#SummaryLabel { color: #7D8589; font-size: 11px; }
QFrame#TopBar, QFrame#CharacterHeader, QFrame#SummaryCard {
    background: #FFFFFF; border: 1px solid #E3DED5; border-radius: 10px;
}
QGroupBox {
    background: #FFFFFF; border: 1px solid #E3DED5; border-radius: 10px;
    margin-top: 14px; padding: 16px 12px 10px 12px; font-weight: 700; color: #3A464C;
}
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 7px; color: #913F4B; }
QPushButton {
    background: #FFFFFF; border: 1px solid #D8D2C8; border-radius: 6px;
    padding: 8px 14px; color: #364249; min-height: 20px;
}
QPushButton:hover { background: #F9F6F0; border-color: #B9AFA1; }
QPushButton:pressed { background: #EEE9E0; }
QPushButton:disabled { color: #ABB0B2; background: #F2F0EB; }
QPushButton#PrimaryButton { background: #913F4B; color: white; border: 1px solid #913F4B; font-weight: 700; }
QPushButton#PrimaryButton:hover { background: #7F3540; }
QPushButton#AccentButton { background: #397B78; color: white; border: 1px solid #397B78; font-weight: 700; }
QPushButton#AccentButton:hover { background: #316C69; }
QPushButton#RowButton { padding: 5px 8px; min-height: 18px; font-size: 12px; color: #71515A; }
QLineEdit, QSpinBox {
    background: #FBFAF7; border: 1px solid #D9D3C9; border-radius: 6px;
    padding: 6px 9px; selection-background-color: #C89199; color: #263138;
}
QLineEdit:focus, QSpinBox:focus { border: 1px solid #A85B65; background: #FFFFFF; }
QSpinBox { min-width: 105px; min-height: 20px; font-weight: 600; }
QSpinBox[dirty="true"] { border: 1px solid #C47B43; background: #FFF8EC; color: #8A4D20; }
QListWidget {
    background: #FFFFFF; border: 1px solid #E3DED5; border-radius: 9px;
    padding: 5px; outline: none;
}
QListWidget::item { border-radius: 7px; padding: 7px 6px; margin: 2px 0; min-height: 44px; }
QListWidget::item:hover { background: #F5F0EA; }
QListWidget::item:selected { background: #F0E3E4; color: #79333D; border-left: 3px solid #913F4B; }
QCheckBox { color: #6B7479; spacing: 5px; }
QCheckBox::indicator { width: 15px; height: 15px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #CFC8BD; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QStatusBar { background: #EDE9E1; color: #677278; border-top: 1px solid #DED8CE; }
QToolTip { background: #303B41; color: white; border: none; padding: 6px; }
"""


def make_icon(text: str, color: str, size: int = 38) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.setPen(QColor("#FFFFFF"))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(13 if len(text) <= 1 else 10)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    painter.end()
    return QIcon(pixmap)


class FieldRow(QWidget):
    write_requested = Signal(str, int)
    lock_requested = Signal(str, bool, int)

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.spec = FIELDS[key]
        self.dirty = False
        self._loading = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        label = QLabel(self.spec.label)
        label.setMinimumWidth(88)
        if self.spec.hint:
            label.setToolTip(self.spec.hint)
            self.setToolTip(self.spec.hint)
        layout.addWidget(label, 1)
        self.spin = QSpinBox()
        self.spin.setRange(self.spec.minimum, self.spec.maximum)
        self.spin.setAccelerated(True)
        self.spin.setKeyboardTracking(False)
        self.spin.setAlignment(Qt.AlignRight)
        self.spin.valueChanged.connect(self._value_changed)
        self.spin.lineEdit().textEdited.connect(self._text_edited)
        self.spin.lineEdit().returnPressed.connect(self._request_write)
        layout.addWidget(self.spin)
        self.write_button = QPushButton("写入")
        self.write_button.setObjectName("RowButton")
        self.write_button.setFixedWidth(52)
        self.write_button.clicked.connect(self._request_write)
        layout.addWidget(self.write_button)
        self.lock = QCheckBox("锁定")
        self.lock.setFixedWidth(54)
        self.lock.toggled.connect(self._lock_changed)
        layout.addWidget(self.lock)

    def _set_dirty(self):
        if self._loading or self.dirty:
            return
        self.dirty = True
        self.spin.setProperty("dirty", True)
        self.spin.style().unpolish(self.spin)
        self.spin.style().polish(self.spin)

    def _value_changed(self, _value: int):
        if not self._loading:
            self._set_dirty()

    def _text_edited(self, _text: str):
        # 键入后立即标记，避免数值尚未提交时被刷新覆盖。
        self._set_dirty()

    def current_value(self) -> int:
        self.spin.interpretText()
        return self.spin.value()

    def has_pending_edit(self) -> bool:
        return self.dirty or self.spin.hasFocus() or self.spin.lineEdit().hasFocus()

    def _request_write(self):
        self.write_requested.emit(self.key, self.current_value())

    def _lock_changed(self, checked: bool):
        self.lock_requested.emit(self.key, checked, self.current_value())

    def set_value(self, value: int, force: bool = False):
        if not force and self.has_pending_edit():
            return
        self._loading = True
        self.spin.setValue(value)
        self._loading = False
        if force:
            self.dirty = False
            self.spin.setProperty("dirty", False)
            self.spin.style().unpolish(self.spin)
            self.spin.style().polish(self.spin)

    def mark_clean(self, value: int):
        self.set_value(value, force=True)

    def set_lock_silent(self, checked: bool):
        self.lock.blockSignals(True)
        self.lock.setChecked(checked)
        self.lock.blockSignals(False)


class CharacterPage(QWidget):
    row_write_requested = Signal(int, str, int)
    page_write_requested = Signal(int, dict)
    row_lock_requested = Signal(int, str, bool, int)
    heal_requested = Signal(int)

    def __init__(self, character: CharacterStats, parent=None):
        super().__init__(parent)
        self.character = character
        self.rows: dict[str, FieldRow] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("CharacterHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        avatar = QLabel(character.name[:1])
        avatar.setFixedSize(52, 52)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"background:{COLORS[character.index % len(COLORS)]};color:white;border-radius:26px;font-size:22px;font-weight:700;")
        header_layout.addWidget(avatar)
        title_box = QVBoxLayout()
        self.name_label = QLabel(character.name)
        self.name_label.setObjectName("CharacterName")
        self.meta_label = QLabel(f"单位编号 {character.unit_id}  ·  人物槽位 {character.index + 1}")
        self.meta_label.setObjectName("CharacterMeta")
        title_box.addWidget(self.name_label)
        title_box.addWidget(self.meta_label)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        heal = QPushButton("HP 回满")
        heal.clicked.connect(lambda: self.heal_requested.emit(character.index))
        header_layout.addWidget(heal)
        root.addWidget(header)

        summary = QFrame()
        summary.setObjectName("SummaryCard")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(14, 9, 14, 9)
        self.summary_values = {}
        for key, label in [("level", "当前等级"), ("bp", "可用 BP"), ("hp", "生命值")]:
            box = QVBoxLayout()
            value = QLabel("-")
            value.setObjectName("SummaryValue")
            value.setAlignment(Qt.AlignCenter)
            caption = QLabel(label)
            caption.setObjectName("SummaryLabel")
            caption.setAlignment(Qt.AlignCenter)
            box.addWidget(value)
            box.addWidget(caption)
            summary_layout.addLayout(box, 1)
            self.summary_values[key] = value
        root.addWidget(summary)

        columns = QHBoxLayout()
        columns.setSpacing(12)
        left = QVBoxLayout()
        right = QVBoxLayout()
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        self._make_group(left, "成长", ["level", "xp", "total_xp", "bp"])
        self._make_group(left, "气力", ["max_zeal", "current_zeal"])
        self._make_group(right, "战斗属性", ["max_hp", "current_hp", "attack", "defense", "speed", "move", "jump"])
        left.addStretch()
        right.addStretch()
        root.addLayout(columns, 1)

        note = QLabel("输入后按回车，或点击该行“写入”；编辑中的数值不会被刷新覆盖。需要同步游戏最新数值时，请点右上角“刷新数值”。")
        note.setStyleSheet("color:#7B8386;font-size:12px;")
        note.setWordWrap(True)
        root.addWidget(note)
        buttons = QHBoxLayout()
        write_page = QPushButton("写入本页")
        write_page.setObjectName("PrimaryButton")
        write_page.clicked.connect(self._write_page)
        buttons.addWidget(write_page)
        revert = QPushButton("撤销未写入修改")
        revert.clicked.connect(self.revert_changes)
        buttons.addWidget(revert)
        buttons.addStretch()
        root.addLayout(buttons)
        self.update_character(character, force=True)

    def _make_group(self, parent_layout: QVBoxLayout, title: str, keys: list[str]):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(5)
        for key in keys:
            row = FieldRow(key)
            row.set_value(self.character.values[key], force=True)
            row.write_requested.connect(self._row_write)
            row.lock_requested.connect(self._row_lock)
            layout.addWidget(row)
            self.rows[key] = row
        parent_layout.addWidget(group)

    def _row_write(self, key: str, value: int):
        self.row_write_requested.emit(self.character.index, key, value)

    def _row_lock(self, key: str, checked: bool, value: int):
        self.row_lock_requested.emit(self.character.index, key, checked, value)

    def _write_page(self):
        values = {key: row.current_value() for key, row in self.rows.items() if row.dirty}
        self.page_write_requested.emit(self.character.index, values)

    def update_character(self, character: CharacterStats, force: bool = False):
        if force or self.character.unit_id != character.unit_id:
            for row in self.rows.values():
                row.dirty = False
                row.set_lock_silent(False)
        self.character = character
        self.name_label.setText(character.name)
        self.meta_label.setText(f"单位编号 {character.unit_id}  ·  人物槽位 {character.index + 1}")
        self.summary_values["level"].setText(str(character.level))
        self.summary_values["bp"].setText(str(character.bp))
        self.summary_values["hp"].setText(f"{character.values['current_hp']} / {character.max_hp}")
        for key, row in self.rows.items():
            if force or (not row.has_pending_edit() and not row.lock.isChecked()):
                row.set_value(character.values[key], force=force)

    def revert_changes(self):
        for key, row in self.rows.items():
            if not row.lock.isChecked():
                row.mark_clean(self.character.values[key])

    def mark_written(self, values: dict[str, int]):
        for key, value in values.items():
            if key in self.rows:
                self.rows[key].mark_clean(value)
                self.character.values[key] = value
        self.summary_values["level"].setText(str(self.character.values["level"]))
        self.summary_values["bp"].setText(str(self.character.values["bp"]))
        self.summary_values["hp"].setText(f"{self.character.values['current_hp']} / {self.character.values['max_hp']}")


class TrainerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.game = GameMemory()
        self.pages: dict[int, CharacterPage] = {}
        self.list_items: dict[int, QListWidgetItem] = {}
        self.locks: dict[tuple[int, str], int] = {}
        self._updating_list = False
        self._lock_error_time = ""
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(make_icon("传", "#913F4B", 64))
        self.resize(1220, 820)
        self.setMinimumSize(980, 700)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(16, 14, 16, 10)
        main.setSpacing(12)
        main.addWidget(self._make_topbar())

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self._make_sidebar())
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.addWidget(self.stack, 1)
        main.addLayout(content, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("请先启动游戏、读取存档，然后点击“连接游戏”。")
        self._make_empty_page()

        # 不在编辑期间自动刷新，避免键入后尚未确认的文本被旧值覆盖。
        self.lock_timer = QTimer(self)
        self.lock_timer.setInterval(500)
        self.lock_timer.timeout.connect(self.enforce_locks)
        self.lock_timer.start()
        QTimer.singleShot(250, self.connect_game)

    def _make_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 12, 18, 12)
        titles = QVBoxLayout()
        title = QLabel("传颂之物：虚伪的假面")
        title.setObjectName("AppTitle")
        subtitle = QLabel("人物属性修改器  ·  v1.1  ·  单机内存版")
        subtitle.setObjectName("AppSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        layout.addLayout(titles)
        layout.addStretch()
        self.connection_label = QLabel("未连接")
        self.connection_label.setStyleSheet("color:#8A5B5B;font-weight:600;")
        layout.addWidget(self.connection_label)
        self.connect_button = QPushButton("连接游戏")
        self.connect_button.setObjectName("AccentButton")
        self.connect_button.clicked.connect(self.connect_game)
        layout.addWidget(self.connect_button)
        self.refresh_button = QPushButton("刷新数值")
        self.refresh_button.clicked.connect(lambda: self.refresh_game(manual=True))
        self.refresh_button.setEnabled(False)
        layout.addWidget(self.refresh_button)
        self.help_button = QPushButton("使用说明")
        self.help_button.clicked.connect(self.show_help)
        layout.addWidget(self.help_button)
        return bar

    def _make_sidebar(self) -> QWidget:
        side = QWidget()
        side.setFixedWidth(250)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)
        title_row = QHBoxLayout()
        title = QLabel("人物列表")
        title.setObjectName("SectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.count_label = QLabel("0 人")
        self.count_label.setStyleSheet("color:#8A9194;")
        title_row.addWidget(self.count_label)
        layout.addLayout(title_row)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索人物…")
        self.search.textChanged.connect(self.filter_characters)
        layout.addWidget(self.search)
        self.character_list = QListWidget()
        self.character_list.currentRowChanged.connect(self.show_character_row)
        layout.addWidget(self.character_list, 1)
        self.heal_button = QPushButton("全员 HP 回满")
        self.heal_button.clicked.connect(self.heal_all)
        self.heal_button.setEnabled(False)
        layout.addWidget(self.heal_button)
        self.bp_button = QPushButton("全员 BP 设为 999")
        self.bp_button.clicked.connect(self.set_all_bp)
        self.bp_button.setEnabled(False)
        layout.addWidget(self.bp_button)
        return side

    def _make_empty_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        label = QLabel("尚未读取人物数据")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size:22px;font-weight:700;color:#7C8589;")
        hint = QLabel("启动游戏并读取存档后，点击右上角“连接游戏”。")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:#92999C;")
        layout.addWidget(label)
        layout.addWidget(hint)
        layout.addStretch()
        self.stack.addWidget(page)

    def connect_game(self):
        try:
            self.game.attach()
            self.locks.clear()
            self.clear_characters()
            characters = self.game.read_characters()
            self.sync_characters(characters)
            self.connection_label.setText(f"已连接  ·  PID {self.game.pid}")
            self.connection_label.setStyleSheet("color:#39736B;font-weight:700;")
            self.connect_button.setText("重新连接")
            self.refresh_button.setEnabled(True)
            self.heal_button.setEnabled(True)
            self.bp_button.setEnabled(True)
            self.stack.setEnabled(True)
            self.status.showMessage(f"已读取 {len(characters)} 个人物页面。游戏版本 MD5 " + ("匹配。" if self.game.version_verified else "不同，但结构校验通过。"), 8000)
            if self.character_list.count():
                self.character_list.setCurrentRow(0)
        except GameNotFoundError as exc:
            self.set_disconnected(str(exc))
        except Exception as exc:
            self.set_disconnected(f"连接失败：{exc}")

    def set_disconnected(self, message: str):
        self.game.close()
        self.locks.clear()
        self.connection_label.setText("未连接")
        self.connection_label.setStyleSheet("color:#8A5B5B;font-weight:600;")
        self.connect_button.setText("连接游戏")
        self.refresh_button.setEnabled(False)
        self.heal_button.setEnabled(False)
        self.bp_button.setEnabled(False)
        self.stack.setEnabled(False)
        self.status.showMessage(message, 10000)

    def clear_characters(self):
        self.character_list.blockSignals(True)
        self.character_list.clear()
        self.character_list.blockSignals(False)
        for page in self.pages.values():
            self.stack.removeWidget(page)
            page.deleteLater()
        self.pages.clear()
        self.list_items.clear()
        self.count_label.setText("0 人")

    def sync_characters(self, characters: list[CharacterStats]):
        current_keys = {(c.index, c.unit_id) for c in characters}
        page_keys = {(index, page.character.unit_id) for index, page in self.pages.items()}
        if current_keys != page_keys:
            selected_index = self.pages[self.stack.currentWidget()].character.index if isinstance(self.stack.currentWidget(), CharacterPage) else 0
            self.locks.clear()
            self.clear_characters()
            for character in characters:
                self.add_character(character)
            self.count_label.setText(f"{len(characters)} 人")
            for row, (index, _item) in enumerate(sorted(self.list_items.items())):
                if index == selected_index:
                    self.character_list.setCurrentRow(row)
                    break
            if self.character_list.currentRow() < 0 and self.character_list.count():
                self.character_list.setCurrentRow(0)
        else:
            for character in characters:
                self.pages[character.index].update_character(character)
                self._update_list_item(character)

    def add_character(self, character: CharacterStats):
        page = CharacterPage(character)
        page.row_write_requested.connect(self.write_row)
        page.page_write_requested.connect(self.write_page)
        page.row_lock_requested.connect(self.change_lock)
        page.heal_requested.connect(self.heal_character)
        self.pages[character.index] = page
        self.stack.addWidget(page)
        item = QListWidgetItem(make_icon(character.name[:1], COLORS[character.index % len(COLORS)]), "")
        item.setData(Qt.UserRole, character.index)
        item.setData(Qt.UserRole + 1, character.name)
        self.character_list.addItem(item)
        self.list_items[character.index] = item
        self._update_list_item(character)

    def _update_list_item(self, character: CharacterStats):
        item = self.list_items.get(character.index)
        if item:
            item.setText(f"{character.name}\nLv. {character.level}    BP {character.bp}")

    def show_character_row(self, row: int):
        item = self.character_list.item(row)
        if not item:
            return
        index = item.data(Qt.UserRole)
        page = self.pages.get(index)
        if page:
            self.stack.setCurrentWidget(page)

    def filter_characters(self, text: str):
        text = text.strip().casefold()
        first_visible = None
        for row in range(self.character_list.count()):
            item = self.character_list.item(row)
            visible = not text or text in item.data(Qt.UserRole + 1).casefold()
            item.setHidden(not visible)
            if visible and first_visible is None:
                first_visible = row
        current_item = self.character_list.currentItem()
        if first_visible is not None and (current_item is None or current_item.isHidden()):
            self.character_list.setCurrentRow(first_visible)

    def refresh_game(self, manual: bool = False):
        if not self.game.connected:
            return
        try:
            characters = self.game.read_characters()
            self.sync_characters(characters)
            if manual:
                self.status.showMessage("数值已刷新；未写入的编辑已保留。", 4000)
        except Exception as exc:
            self.set_disconnected(f"游戏连接已中断：{exc}")

    def _perform_write(self, index: int, values: dict[str, int]) -> bool:
        page = self.pages.get(index)
        if not page or not values:
            return False
        try:
            verified = self.game.write_values(page.character, values)
            page.mark_written({key: verified[key] for key in values})
            self._update_list_item(page.character)
            return True
        except (MemoryWriteError, ValueError, OSError) as exc:
            self.status.showMessage(f"写入失败：{exc}", 7000)
            return False
        except Exception as exc:
            self.status.showMessage(f"写入失败：{exc}", 7000)
            return False

    def write_row(self, index: int, key: str, value: int):
        if self._perform_write(index, {key: value}):
            self.status.showMessage(f"{self.pages[index].character.name} · {FIELDS[key].label} 已写入并校验：{value}", 5000)

    def write_page(self, index: int, values: dict[str, int]):
        if not values:
            self.status.showMessage("本页没有尚未写入的修改。", 4000)
            return
        if self._perform_write(index, values):
            self.status.showMessage(f"{self.pages[index].character.name} 的 {len(values)} 项修改已写入并校验。", 5000)

    def change_lock(self, index: int, key: str, checked: bool, value: int):
        lock_key = (index, key)
        if checked:
            if self._perform_write(index, {key: value}):
                self.locks[lock_key] = value
                self.status.showMessage(f"已锁定 {self.pages[index].character.name} · {FIELDS[key].label}。", 4000)
            else:
                self.pages[index].rows[key].set_lock_silent(False)
        else:
            self.locks.pop(lock_key, None)
            self.status.showMessage(f"已解除 {self.pages[index].character.name} · {FIELDS[key].label} 锁定。", 3000)

    def enforce_locks(self):
        if not self.game.connected or not self.locks:
            return
        for (index, key), value in list(self.locks.items()):
            page = self.pages.get(index)
            if not page:
                self.locks.pop((index, key), None)
                continue
            try:
                current = self.game.read_character(index)
                if current.values[key] != value:
                    self.game.write_values(current, {key: value})
            except Exception:
                now = datetime.now().strftime("%H:%M:%S")
                if now != self._lock_error_time:
                    self._lock_error_time = now
                    self.status.showMessage("部分锁定值暂时无法写入；读档或战斗切换后请检查。", 3000)

    def heal_character(self, index: int):
        page = self.pages.get(index)
        if page and self._perform_write(index, {"current_hp": page.character.max_hp}):
            self.status.showMessage(f"{page.character.name} 的 HP 已回满。", 4000)

    def heal_all(self):
        try:
            count = self.game.heal_all()
            self.refresh_game()
            self.status.showMessage(f"已为 {count} 名人物回满 HP。", 5000)
        except Exception as exc:
            self.status.showMessage(f"全员回血失败：{exc}", 7000)

    def set_all_bp(self):
        dialog = QMessageBox(QMessageBox.Question, "确认批量修改", "确定要将当前所有人物的 BP 都设为 999 吗？", QMessageBox.Yes | QMessageBox.No, self)
        dialog.button(QMessageBox.Yes).setText("设为 999")
        dialog.button(QMessageBox.No).setText("取消")
        if dialog.exec() != QMessageBox.Yes:
            return
        try:
            count = self.game.set_all_bp(999)
            self.refresh_game()
            self.status.showMessage(f"已将 {count} 名人物的 BP 设为 999。", 5000)
        except Exception as exc:
            self.status.showMessage(f"批量修改 BP 失败：{exc}", 7000)

    def show_help(self):
        dialog = QMessageBox(QMessageBox.Information, "使用说明", (
            "1. 先启动《传颂之物：虚伪的假面》，读取一个存档。\n"
            "2. 点击“连接游戏”，左侧选择人物。\n"
            "3. 修改数值后，点击该行“写入”或底部“写入本页”。\n"
            "4. 切换游戏内人物页面或进入下一场战斗，即可看到效果；之后正常保存游戏。\n\n"
            "锁定：每 0.5 秒持续写入该值，适合游戏会自动重算的移动、跳跃等项目。不需要时请解除。\n\n"
            "刷新：界面不会自动刷新，避免覆盖正在输入的内容；需要同步游戏里的最新数值时，点击右上角“刷新数值”。\n\n"
            "注意：本工具只修改运行中的内存，不改动游戏 exe，也不会自动改写存档。读档、重开或战斗切换后，部分数值可能被游戏重算，请刷新后重新写入。建议提前备份重要存档，仅用于单机游戏。"
        ), QMessageBox.Ok, self)
        dialog.button(QMessageBox.Ok).setText("知道了")
        dialog.exec()

    def closeEvent(self, event: QCloseEvent):
        self.lock_timer.stop()
        self.game.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = TrainerWindow()
    window.show()
    if "--self-test" in sys.argv:
        def finish_test():
            window.refresh_game()
            pages = len(window.pages)
            fields = len(window.pages[0].rows) if window.pages else 0
            ok = window.game.connected and pages >= 18 and fields == 13
            output = Path.cwd()
            window.grab().save(str(output / "packaged-preview.png"), "PNG")
            (output / "packaged-smoke.txt").write_text(
                f"status={'OK' if ok else 'FAIL'}\npages={pages}\nfields={fields}\npid={window.game.pid}\n",
                encoding="utf-8",
            )
            app.exit(0 if ok else 2)
        QTimer.singleShot(1600, finish_test)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
