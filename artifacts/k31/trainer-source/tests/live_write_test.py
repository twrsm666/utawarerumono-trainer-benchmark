from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game_memory import GameMemory


def main():
    game = GameMemory()
    game.attach()
    character = game.read_characters()[0]
    original = character.values["bp"]
    test_value = original + 1 if original < 9999 else original - 1
    written = False
    restored = False
    try:
        result = game.write_values(character, {"bp": test_value})
        assert result["bp"] == test_value, "写入校验值不一致"
        reread = game.read_character(character.index)
        assert reread.values["bp"] == test_value, "重新读取值不一致"
        written = True
    finally:
        latest = game.read_character(character.index)
        result = game.write_values(latest, {"bp": original})
        assert result["bp"] == original, "还原校验值不一致"
        restored = True
        game.close()
    assert written and restored
    print(f"LIVE_WRITE_OK name={character.name} original_bp={original} test_bp={test_value} restored_bp={original}")


if __name__ == "__main__":
    main()
