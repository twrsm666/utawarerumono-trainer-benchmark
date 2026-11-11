from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game_memory import CHARACTER_STRIDE, CORE_CHARACTER_COUNT, CORE_UNITS, FIELDS, FIELD_ORDER, parse_character


class OfflineStructureTests(unittest.TestCase):
    def make_record(self, index=0):
        data = bytearray(CHARACTER_STRIDE * 30)
        base = index * CHARACTER_STRIDE
        struct.pack_into("<H", data, base + 0x74, 20)
        struct.pack_into("<I", data, base + 0x12C, 1)
        expected = {
            "level": 12, "xp": 345, "total_xp": 67890, "bp": 77,
            "max_hp": 1234, "current_hp": 1200, "attack": 111,
            "defense": 99, "speed": 108, "move": 5, "jump": 3,
            "max_zeal": 180, "current_zeal": 90,
        }
        for key, value in expected.items():
            spec = FIELDS[key]
            struct.pack_into(spec.fmt, data, base + spec.offset, value)
        return data, expected

    def test_parse_character(self):
        data, expected = self.make_record(1)
        character = parse_character(data, 1)
        self.assertEqual(character.unit_id, 20)
        self.assertEqual(character.name, "久远")
        self.assertEqual(character.team, 1)
        self.assertEqual(character.values, expected)

    def test_field_order_is_complete(self):
        self.assertEqual(set(FIELD_ORDER), set(FIELDS))
        self.assertEqual(len(FIELD_ORDER), 13)

    def test_fields_stay_inside_record(self):
        for spec in FIELDS.values():
            self.assertGreaterEqual(spec.offset, 0)
            self.assertLessEqual(spec.offset + spec.size, CHARACTER_STRIDE)
            self.assertLessEqual(spec.minimum, spec.maximum)

    def test_expected_core_roster(self):
        self.assertEqual(len(CORE_UNITS), CORE_CHARACTER_COUNT)
        self.assertEqual(len({unit_id for unit_id, _name in CORE_UNITS}), CORE_CHARACTER_COUNT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
