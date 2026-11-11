from __future__ import annotations

import ctypes
import hashlib
import struct
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

PROCESS_NAME = "Utawarerumono Mask of Deception.exe"
SUPPORTED_MD5 = "c02107b577a8e3be7965b5b50594abfc"
CHARACTER_TABLE_RVA = 0x6CE4A4
CHARACTER_STRIDE = 0x278
CORE_CHARACTER_COUNT = 18
PLAYER_TABLE_COUNT = 30

PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class GameNotFoundError(RuntimeError):
    pass


class GameVersionError(RuntimeError):
    pass


class MemoryWriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    offset: int
    fmt: str
    minimum: int
    maximum: int
    group: str
    hint: str = ""

    @property
    def size(self) -> int:
        return struct.calcsize(self.fmt)


FIELDS = {
    spec.key: spec
    for spec in [
        FieldSpec("level", "等级", 0x7C, "<H", 1, 99, "成长", "修改后切换一次人物页面可刷新游戏显示。"),
        FieldSpec("xp", "当前经验", 0x7E, "<H", 0, 65535, "成长", "战斗结算后会按游戏规则升级。"),
        FieldSpec("total_xp", "累计经验", 0x84, "<I", 0, 99999999, "成长"),
        FieldSpec("bp", "奖励点数 BP", 0xA8, "<H", 0, 9999, "成长", "用于角色培养；如被重算，可启用锁定。"),
        FieldSpec("max_hp", "最大 HP", 0x88, "<I", 1, 99999, "战斗属性"),
        FieldSpec("current_hp", "当前 HP", 0xB8, "<I", 0, 99999, "战斗属性", "战斗外通常与最大 HP 相同。"),
        FieldSpec("attack", "攻击 ATK", 0x8C, "<H", 0, 9999, "战斗属性"),
        FieldSpec("defense", "防御 DEF", 0x8E, "<H", 0, 9999, "战斗属性"),
        FieldSpec("speed", "速度 SPD", 0x90, "<H", 0, 9999, "战斗属性"),
        FieldSpec("move", "移动 MOVE", 0x94, "<H", 0, 30, "战斗属性", "部分界面会重算移动，需要锁定时可勾选锁定。"),
        FieldSpec("jump", "跳跃 JUMP", 0x96, "<H", 0, 30, "战斗属性", "部分界面会重算跳跃，需要锁定时可勾选锁定。"),
        FieldSpec("max_zeal", "最大气力", 0x80, "<I", 0, 99999, "气力", "游戏通常以 100 为基础值。"),
        FieldSpec("current_zeal", "当前气力", 0xBC, "<I", 0, 99999, "气力"),
    ]
}

FIELD_ORDER = [
    "level", "xp", "total_xp", "bp",
    "max_hp", "current_hp", "attack", "defense", "speed", "move", "jump",
    "max_zeal", "current_zeal",
]

CORE_UNITS = [
    (0, "哈克"),
    (20, "久远"),
    (25, "麻吕吕"),
    (28, "露露缇耶"),
    (32, "乌露露・萨拉娜"),
    (33, "鵟"),
    (35, "扇"),
    (36, "猫音"),
    (37, "奇羽琉"),
    (38, "阿图依"),
    (42, "杏树"),
    (43, "亚库托瓦尔特"),
    (47, "宗近"),
    (50, "芙米露露"),
    (102, "伊塔库"),
    (103, "尤里"),
    (112, "环"),
    (114, "莎莎菈"),
]

UNIT_NAMES = {
    0: "哈克", 1: "哈克", 4: "奥修特尔", 12: "奥修特尔", 13: "奥修特尔", 14: "右近",
    20: "久远", 21: "久远", 22: "久远", 25: "麻吕吕", 27: "露露缇耶", 28: "露露缇耶",
    30: "乌露露", 31: "萨拉娜", 32: "乌露露・萨拉娜", 33: "鵟", 34: "鵟", 35: "扇",
    36: "猫音", 37: "奇羽琉", 38: "阿图依", 39: "阿图依", 40: "杏树", 41: "杏树", 42: "杏树",
    43: "亚库托瓦尔特", 44: "亚库托瓦尔特", 46: "诗诺农", 47: "宗近", 48: "宗近",
    50: "芙米露露", 51: "藤香", 52: "卡露拉", 53: "卡缪", 54: "阿露露", 56: "克罗",
    57: "贝纳威", 58: "乌露托莉", 63: "穗香", 64: "御雷", 66: "左近", 83: "武赖",
    87: "雷光", 89: "七理夜", 93: "恩图亚", 96: "时樱", 102: "伊塔库", 103: "尤里",
    112: "环", 113: "环", 114: "莎莎菈", 115: "莎莎菈",
}


@dataclass
class CharacterStats:
    index: int
    unit_id: int
    name: str
    team: int
    values: dict[str, int]
    is_guest: bool = False

    @property
    def level(self) -> int:
        return self.values["level"]

    @property
    def max_hp(self) -> int:
        return self.values["max_hp"]

    @property
    def bp(self) -> int:
        return self.values["bp"]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256), ("szExePath", wintypes.WCHAR * 260),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32FirstW.restype = wintypes.BOOL
kernel32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32NextW.restype = wintypes.BOOL
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = wintypes.BOOL


def _unpack(data: bytes, offset: int, fmt: str) -> int:
    return struct.unpack_from(fmt, data, offset)[0]


def parse_character(data: bytes, index: int) -> CharacterStats:
    base = index * CHARACTER_STRIDE
    unit_id = _unpack(data, base + 0x74, "<H")
    team = _unpack(data, base + 0x12C, "<I")
    values = {key: _unpack(data, base + spec.offset, spec.fmt) for key, spec in FIELDS.items()}
    is_guest = index >= CORE_CHARACTER_COUNT
    name = UNIT_NAMES.get(unit_id, f"人物 {unit_id}")
    if is_guest:
        name = f"{name}（临时）"
    return CharacterStats(index, unit_id, name, team, values, is_guest)


class GameMemory:
    def __init__(self):
        self.handle = None
        self.pid = 0
        self.module_base = 0
        self.table_address = 0
        self.executable_path = ""
        self.executable_md5 = ""

    @property
    def connected(self) -> bool:
        return bool(self.handle)

    @property
    def version_verified(self) -> bool:
        return self.executable_md5 == SUPPORTED_MD5

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
        self.handle = None
        self.pid = 0
        self.module_base = 0
        self.table_address = 0

    def attach(self):
        self.close()
        self.pid = self._find_process()
        access = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
        self.handle = kernel32.OpenProcess(access, False, self.pid)
        if not self.handle:
            self.pid = 0
            raise PermissionError(ctypes.WinError(ctypes.get_last_error()))
        try:
            self.module_base, self.executable_path = self._find_module()
            self.table_address = self.module_base + CHARACTER_TABLE_RVA
            data = self._read(self.table_address, CHARACTER_STRIDE * PLAYER_TABLE_COUNT)
            core = [parse_character(data, i) for i in range(CORE_CHARACTER_COUNT)]
            matches = sum(character.unit_id == expected for character, (expected, _) in zip(core, CORE_UNITS))
            valid = all(character.team == 1 and 1 <= character.level <= 99 and character.max_hp > 0 for character in core[:3])
            if matches < 15 or not valid:
                raise GameVersionError("人物表校验失败。请确认游戏版本，并先读取一个存档后再连接。")
            self.executable_md5 = hashlib.md5(Path(self.executable_path).read_bytes()).hexdigest()
            return len(core)
        except Exception:
            self.close()
            raise

    def _find_process(self) -> int:
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(entry)
            ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
            while ok:
                if entry.szExeFile.casefold() == PROCESS_NAME.casefold():
                    return entry.th32ProcessID
                ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
            raise GameNotFoundError("未检测到游戏。请先启动游戏并读取存档，然后点击“连接游戏”。")
        finally:
            kernel32.CloseHandle(snapshot)

    def _find_module(self) -> tuple[int, str]:
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid)
        if snapshot == INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            entry = MODULEENTRY32W()
            entry.dwSize = ctypes.sizeof(entry)
            ok = kernel32.Module32FirstW(snapshot, ctypes.byref(entry))
            while ok:
                if entry.szModule.casefold() == PROCESS_NAME.casefold():
                    address = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value
                    return address, entry.szExePath
                ok = kernel32.Module32NextW(snapshot, ctypes.byref(entry))
            raise GameVersionError("无法取得游戏主模块基址。")
        finally:
            kernel32.CloseHandle(snapshot)

    def _read(self, address: int, size: int) -> bytes:
        if not self.handle:
            raise GameNotFoundError("尚未连接游戏。")
        buffer = (ctypes.c_ubyte * size)()
        read = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(self.handle, address, buffer, size, ctypes.byref(read)) or read.value != size:
            raise ctypes.WinError(ctypes.get_last_error())
        return bytes(buffer)

    def _write(self, address: int, data: bytes):
        if not self.handle:
            raise GameNotFoundError("尚未连接游戏。")
        buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        written = ctypes.c_size_t()
        if not kernel32.WriteProcessMemory(self.handle, address, buffer, len(data), ctypes.byref(written)) or written.value != len(data):
            raise ctypes.WinError(ctypes.get_last_error())

    def read_characters(self, include_empty_guests: bool = False) -> list[CharacterStats]:
        data = self._read(self.table_address, CHARACTER_STRIDE * PLAYER_TABLE_COUNT)
        characters = [parse_character(data, i) for i in range(PLAYER_TABLE_COUNT)]
        result = characters[:CORE_CHARACTER_COUNT]
        for character in characters[CORE_CHARACTER_COUNT:]:
            occupied = character.team == 1 and character.unit_id and character.level > 0 and character.max_hp > 0
            if include_empty_guests or occupied:
                result.append(character)
        return result

    def read_character(self, index: int) -> CharacterStats:
        if not 0 <= index < PLAYER_TABLE_COUNT:
            raise ValueError("人物索引无效。")
        data = self._read(self.table_address + index * CHARACTER_STRIDE, CHARACTER_STRIDE)
        return self._parse_single(data, index)

    @staticmethod
    def _parse_single(data: bytes, index: int) -> CharacterStats:
        unit_id = _unpack(data, 0x74, "<H")
        team = _unpack(data, 0x12C, "<I")
        values = {key: _unpack(data, spec.offset, spec.fmt) for key, spec in FIELDS.items()}
        is_guest = index >= CORE_CHARACTER_COUNT
        name = UNIT_NAMES.get(unit_id, f"人物 {unit_id}")
        if is_guest:
            name += "（临时）"
        return CharacterStats(index, unit_id, name, team, values, is_guest)

    def write_values(self, character: CharacterStats, values: dict[str, int]) -> dict[str, int]:
        if not values:
            return {}
        current = self.read_character(character.index)
        if current.unit_id != character.unit_id or current.team != 1:
            raise MemoryWriteError(f"{character.name} 的内存对象已变化，请刷新后重试。")
        normalized = {}
        for key, value in values.items():
            if key not in FIELDS:
                raise ValueError(f"未知属性: {key}")
            spec = FIELDS[key]
            value = int(value)
            if not spec.minimum <= value <= spec.maximum:
                raise ValueError(f"{spec.label} 必须在 {spec.minimum}～{spec.maximum} 之间。")
            normalized[key] = value
        for key, value in normalized.items():
            spec = FIELDS[key]
            address = self.table_address + character.index * CHARACTER_STRIDE + spec.offset
            self._write(address, struct.pack(spec.fmt, value))
        verified = self.read_character(character.index)
        failed = [key for key, value in normalized.items() if verified.values[key] != value]
        if failed:
            labels = "、".join(FIELDS[key].label for key in failed)
            raise MemoryWriteError(f"写入后校验失败：{labels}。游戏可能正在重算该值，可尝试锁定。")
        return verified.values

    def heal_all(self) -> int:
        count = 0
        for character in self.read_characters():
            if character.team == 1 and character.level > 0:
                self.write_values(character, {"current_hp": character.max_hp})
                count += 1
        return count

    def set_all_bp(self, value: int = 999) -> int:
        count = 0
        for character in self.read_characters():
            if character.team == 1 and character.level > 0:
                self.write_values(character, {"bp": value})
                count += 1
        return count
