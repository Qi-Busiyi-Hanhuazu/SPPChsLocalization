import json
import os
import struct
from typing import Any, Generator

from helper import (
  CHAR_TABLE_PATH,
  DIR_TEXT_FILES,
  get_used_characters_by_usage,
)


def generate_cp932() -> Generator[tuple[int, str], Any, None]:
  initial_code = 0x829F

  for high in range(0x81, 0xA0):
    for low in range(0x40, 0xFD):
      if low == 0x7F:
        continue
      code = (high << 8) | low
      if code < initial_code:
        continue
      try:
        char = struct.pack(">H", code).decode("shift-jis")

      except UnicodeDecodeError:
        continue
      yield code, char


def generate_char_table(json_root: str) -> dict[str, str]:
  characters = get_used_characters_by_usage(json_root)
  generator = generate_cp932()

  char_table = {}

  for char in characters:
    if 0x4E00 <= ord(char) <= 0x9FFF:
      cp932_code, cp932_char = next(generator)
      char_table[cp932_char] = char

  return char_table


if __name__ == "__main__":
  char_table = generate_char_table(f"{DIR_TEXT_FILES}/zh_Hans")
  os.makedirs(os.path.dirname(CHAR_TABLE_PATH), exist_ok=True)
  with open(CHAR_TABLE_PATH, "w", -1, "utf8") as writer:
    json.dump(char_table, writer, ensure_ascii=False, indent=2)
  print(f"Collected {len(char_table)} characters.")
