import json
import os
import struct
import math
from typing import Callable

from PIL import Image, ImageDraw, ImageFont


from helper import CHAR_TABLE_PATH, DIR_ARM9_PATCH, DIR_ARM9_PATCH_ADDITIONAL, DIR_ORIGINAL_FILES

BLANK_BLOCKS = ((0x8040, 0x8140), (0x84BF, 0x889F))


FONT_OFFSET = 0xEE3A8
FONT_END = 0xFDF28
FONT_MAX_SIZE = FONT_END - FONT_OFFSET


class Character:
  def __init__(self, code: int, char: str, offset: int, data: bytes = None):
    self.code = code
    self.char = char
    self.offset = offset
    self.data = data or b"\0" * 32

  def __repr__(self) -> str:
    return f"Character({hex(self.code)}, {hex(self.index)}, {self.char}, {hex(self.offset)})"

  @staticmethod
  def code_to_index(code: int):
    hi = (code >> 8) & 0xFF
    lo = code & 0xFF
    return (hi - 0x80) * 0xC0 + (lo - 0x40)

  @staticmethod
  def index_to_code(index: int):
    hi = (index // 0xC0) + 0x80
    lo = (index % 0xC0) + 0x40
    return (hi << 8) | lo

  @property
  def index(self) -> int:
    return self.code_to_index(self.code)


def parse_characters_from_bytes(
  data: bytes,
) -> list[Character]:
  characters: list[Character] = []

  def temp():
    default_offset = 0

    for hi in range(0x81, 0xA0):
      for lo in range(0x40, 0xFF):
        code = hi * 0x100 + lo
        try:
          char = struct.pack(">H", code).decode("shift-jis")
        except UnicodeDecodeError:
          continue
        offset_offset = Character.code_to_index(code) * 4
        if offset_offset + 4 >= len(data):
          return
        (data_offset,) = struct.unpack("<I", data[offset_offset : offset_offset + 4])
        if code == 0x8140:
          # Full-width space '　'
          default_offset = data_offset
        elif data_offset == default_offset or data_offset == 0:
          continue
        offset = data_offset - 4
        if offset + 0x22 >= len(data):
          return
        (unk_value,) = struct.unpack("<H", data[offset : offset + 0x02])

        if unk_value != 0x0208:
          return
        char_data = data[offset + 0x02 : offset + 0x22]

        characters.append(Character(code, char, offset, char_data))

  temp()
  return characters


def convert_characters_to_image(
  characters: list[Character],
  font: ImageFont.FreeTypeFont = None,
) -> Image.Image:
  rows = 32
  cols = math.ceil(len(characters) / rows)
  char_width = 16
  char_height = 48
  image = Image.new("L", (char_width * rows, char_height * cols), 0xFF)
  draw = ImageDraw.Draw(image)
  if font is None:
    font = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 14)

  for index, character in enumerate(characters):
    y = index // rows
    x = index % rows

    x2, y2 = 0, 0
    for byte in character.data:
      pixels = [byte & 0b11, (byte >> 2) & 0b11, (byte >> 4) & 0b11, (byte >> 6) & 0b11]
      for i in range(4):
        image.putpixel((x * char_width + x2 + 4, y * char_height + y2), (3 - pixels[i]) * 0x55)
        x2 += 1

      if x2 == 8:
        x2 = 0
        y2 += 1

    draw.text(
      (x * char_width + 2, y * char_height + 30),
      character.char,
      0x00,
      font,
      "ls",
    )

  return image


def update_characters(
  characters: list[Character],
  char_table: dict[str, str],
  char_handler: Callable[[str], bytes],
) -> list[Character]:
  new_characters = {}
  for character in characters:
    if 0x3040 <= ord(character.char) <= 0x30FF:
      continue
    if 0x4E00 <= ord(character.char) <= 0x9FFF:
      continue

    new_characters[character.code] = character

  for key, value in char_table.items():
    (code,) = struct.unpack(">H", key.encode("shift-jis"))

    new_bytes = char_handler(value)
    if len(new_bytes) != 32:
      raise ValueError(f"Invalid size for character {key}: {len(new_bytes)}")

    new_characters[code] = Character(code, key, 0, new_bytes)

  return sorted(new_characters.values(), key=lambda x: x.code)


def get_next_offset(max_char_index: int):
  index = 0
  offset = 0
  for blank_block_start, blank_block_end in BLANK_BLOCKS:
    offset = Character.code_to_index(blank_block_start) * 0x04
    offset_end = Character.code_to_index(blank_block_end) * 0x04
    while offset + 0x22 < offset_end:
      yield offset
      offset += 0x22
      index += 1

  offset = (max_char_index + 1) * 0x04
  while True:
    yield offset
    offset += 0x22
    index += 1


def build_new_bytes(characters: list[Character], max_size: int) -> bytes:
  output = bytearray(max_size)

  generator = get_next_offset(characters[-1].index)

  for character in characters:
    character.offset = next(generator)
    offset_offset = character.index * 4
    output[offset_offset : offset_offset + 4] = struct.pack("<I", character.offset + 4)
    output[character.offset : character.offset + 0x22] = b"\x08\x02" + character.data

  return bytes(output)


if __name__ == "__main__":
  with open(f"{DIR_ORIGINAL_FILES}/arm9.bin", "rb") as reader:
    data = reader.read()

  characters = parse_characters_from_bytes(data[FONT_OFFSET:FONT_END])

  with open(CHAR_TABLE_PATH, "r", -1, "utf8") as reader:
    char_table: dict[str, str] = json.load(reader)

  colors = (0xFF, 0xFF, 0xFF, 0xAA, 0xAA, 0xAA, 0x55, 0x55, 0x55, 0x00, 0x00, 0x00)
  palette = Image.new("P", (8, 8))
  palette.putpalette(colors)

  muzai = ImageFont.truetype("files/fonts/MZPXorig.ttf", 12)

  def draw_with_muzai_pixel(char: str) -> bytes:
    tile = Image.new("RGB", (8, 16), (0xFF, 0xFF, 0xFF))
    draw = ImageDraw.Draw(tile)
    draw.text((0, 14), f"{char}　　黑鼠龙龟", (0x00, 0x00, 0x00), muzai, "ls")
    tile = tile.quantize(palette=palette, dither=Image.Dither.NONE)

    tile_data = tile.tobytes()
    new_bytes = bytearray()
    for i in range(0, len(tile_data), 4):
      byte = tile_data[i] | (tile_data[i + 1] << 2) | (tile_data[i + 2] << 4) | (tile_data[i + 3] << 6)
      new_bytes.append(byte)

    return bytes(new_bytes)

  characters = update_characters(
    characters,
    char_table,
    draw_with_muzai_pixel,
  )

  new_bytes = build_new_bytes(characters, FONT_MAX_SIZE)
  with open(f"{DIR_ARM9_PATCH}/{DIR_ARM9_PATCH_ADDITIONAL}/repl_{0x2000000 + FONT_OFFSET:07X}.bin", "wb") as writer:
    writer.write(new_bytes)
