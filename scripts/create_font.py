import json
import math
import struct
from typing import Callable

from helper import (
  CHAR_TABLE_PATH,
  DIR_ARM9_PATCH,
  DIR_ARM9_PATCH_GENERATED,
  DIR_ORIGINAL_FILES,
)
from PIL import Image, ImageDraw, ImageFont

FONT_OFFSET = 0xEE3A8
FONT_END = 0xFDF28
FONT_MAX_SIZE = FONT_END - FONT_OFFSET - 0x200

FONT_BINARY_SIZE_ORIGINAL = 0x22
FONT_BINARY_SIZE_NEW = 36
CHARACTER_WIDTH = 12
CHARACTER_HEIGHT = 12


class Character:
  def __init__(self, code: int, char: str, offset: int, data: bytes | None = None):
    self.code = code
    self.char = char
    self.offset = offset
    self.data = ((data or b"") + b"\0" * FONT_BINARY_SIZE_NEW)[:FONT_BINARY_SIZE_NEW]

  def __repr__(self) -> str:
    return f"Character({hex(self.code)}, {hex(self.index)}, {self.char}, {hex(self.offset)})"

  @staticmethod
  def code_to_index(code: int):
    hi = (code >> 8) & 0xFF
    lo = code & 0xFF
    return (hi & 0x3F) * 0xC0 + (lo - 0x40)

  @staticmethod
  def index_to_code(index: int):
    hi = (index // 0xC0) + 0x80
    if hi > 0x9F:
      # 0xE0-0xEF
      hi += 0x40
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
          char = struct.pack(">H", code).decode("cp932")
        except UnicodeDecodeError:
          continue
        offset_offset = Character.code_to_index(code) * 4
        if offset_offset + 4 > len(data):
          return
        (data_offset,) = struct.unpack("<I", data[offset_offset : offset_offset + 4])
        if code == 0x8140:
          # Full-width space '　'
          default_offset = data_offset
        elif data_offset == default_offset or data_offset == 0:
          continue
        offset = data_offset - 4
        if offset + FONT_BINARY_SIZE_ORIGINAL > len(data):
          return
        (unk_value,) = struct.unpack("<H", data[offset : offset + 0x02])

        if unk_value != 0x0208:
          return
        char_data = data[offset + 0x02 : offset + FONT_BINARY_SIZE_ORIGINAL]

        characters.append(Character(code, char, offset, char_data))

  temp()
  return characters


def convert_characters_to_image(
  characters: list[Character],
  font: ImageFont.FreeTypeFont | None = None,
) -> Image.Image:
  colors = (0xFF, 0xFF, 0xFF, 0xAA, 0xAA, 0xAA, 0x55, 0x55, 0x55, 0x00, 0x00, 0x00)

  rows = 64
  cols = math.ceil(len(characters) / rows)
  char_width = 16
  char_height = 48
  full_image = Image.new("L", (char_width * rows, char_height * cols), 0xFF)
  draw = ImageDraw.Draw(full_image)
  if font is None:
    font = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 14)

  for index, character in enumerate(characters):
    y = index // rows
    x = index % rows

    pixels = bytearray()
    for byte in character.data:
      pixels.extend([byte & 0b11, (byte >> 2) & 0b11, (byte >> 4) & 0b11, (byte >> 6) & 0b11])
    tile = Image.frombytes("P", (CHARACTER_WIDTH, CHARACTER_HEIGHT), bytes(pixels))
    tile.putpalette(colors)

    full_image.paste(tile, (x * char_width + 4, y * char_height + 8))

    draw.text(
      (x * char_width + 2, y * char_height + 38),
      character.char,
      0x00,
      font,
      "ls",
    )

  return full_image


def update_characters(
  draw_characters: dict[str, str],
  char_handler: Callable[[str], bytes],
) -> list[Character]:
  new_characters = {}
  for key, value in draw_characters.items():
    (code,) = struct.unpack(">H", key.encode("cp932"))

    new_bytes = char_handler(value)
    if len(new_bytes) != FONT_BINARY_SIZE_NEW:
      raise ValueError(f"Invalid size for character {key}: {len(new_bytes)}")

    new_characters[code] = Character(code, key, 0, new_bytes)

  return sorted(new_characters.values(), key=lambda x: x.code)


def get_next_offset(max_char_index: int, sizes: list[int]):
  blocks = [
    (Character.code_to_index(start) * 4, Character.code_to_index(end) * 4)
    for start, end in ((0x8040, 0x8140), (0x84BF, 0x889F))
  ]
  blocks.append(((max_char_index + 1) * 4, FONT_MAX_SIZE))
  block = 0
  offset = blocks[block][0]
  for size in sizes:
    while offset + size > blocks[block][1]:
      block += 1
      offset = blocks[block][0]
    yield offset
    offset += size


def build_new_bytes(characters: list[Character], max_size: int) -> bytes:
  output = bytearray(max_size)

  generator = get_next_offset(characters[-1].index, [len(character.data) for character in characters])

  for character in characters:
    character.offset = next(generator)
    offset_offset = character.index * 4
    output[offset_offset : offset_offset + 4] = struct.pack("<I", character.offset + 4)
    output[character.offset : character.offset + len(character.data)] = character.data
    print(f"{character.offset:08X}\t{character.char}")

  return bytes(output)


def main():
  simsun = ImageFont.truetype("C:/Windows/Fonts/simsun.ttc", 12)
  ms_gothic = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 12)

  def get_font(char: str) -> ImageFont.FreeTypeFont:
    if 0x4E00 <= ord(char) <= 0x9FFF:
      return simsun

    if char in "，。！？:;“”‘’·—…～":
      return simsun

    return ms_gothic

  def get_position(font: ImageFont.FreeTypeFont, char: str) -> tuple[int, int]:
    if char in "“”‘’":
      # y - 1
      return (0, 9)
    elif char in "！？…":
      # y + 1
      return (0, 11)
    elif char in "，：；":
      # y + 2
      return (0, 12)
    elif char in "。":
      # y + 3
      return (0, 13)

    if font is simsun:
      return (0, 10)

    return (0, 11)

  def filter(character: Character):
    if 0x4E00 <= ord(character.char) <= 0x9FFF:
      return False
    return True

  with open(f"{DIR_ORIGINAL_FILES}/arm9.bin", "rb") as reader:
    data = reader.read()

  characters = parse_characters_from_bytes(data[FONT_OFFSET:FONT_END])
  original_characters = {character.char: character.data[:32] for character in characters}
  draw_characters = {c.char: c.char for c in characters if filter(c)}

  with open(CHAR_TABLE_PATH, "r", -1, "utf8") as reader:
    char_table: dict[str, str] = json.load(reader)

  draw_characters.update(char_table)

  colors = (0xFF, 0xFF, 0xFF, 0xAA, 0xAA, 0xAA, 0x55, 0x55, 0x55, 0x00, 0x00, 0x00)
  palette = Image.new("P", (8, 8))
  palette.putpalette(colors)

  def draw_char(char: str) -> bytes:
    tile = Image.new("RGB", (CHARACTER_WIDTH, CHARACTER_HEIGHT), (0xFF, 0xFF, 0xFF))
    draw = ImageDraw.Draw(tile)
    font = get_font(char)
    draw.text(get_position(font, char), f"{char}　　黑鼠龙龟", (0x00, 0x00, 0x00), font, "ls")
    tile = tile.quantize(palette=palette, dither=Image.Dither.NONE)

    tile_data = tile.tobytes()
    new_bytes = bytearray()
    for i in range(0, len(tile_data), 4):
      byte = 0
      for b in range(4):
        byte |= tile_data[i + b] << (b * 2)
      new_bytes.append(byte)

    return bytes(new_bytes)

  characters = update_characters(
    draw_characters,
    draw_char,
  )

  with open("texts/ja/000E8A54.json", "r", -1, "utf8") as reader:
    credits = json.load(reader)
  credit_characters = set("".join(record["original"] for record in credits))
  for character in characters:
    if character.char in credit_characters:
      character.data += b"\x08\x02" + original_characters[character.char]

  new_bytes = build_new_bytes(characters, FONT_MAX_SIZE)
  with open(f"{DIR_ARM9_PATCH}/{DIR_ARM9_PATCH_GENERATED}/repl_{0x2000000 + FONT_OFFSET:07X}.bin", "wb") as writer:
    writer.write(new_bytes)

  convert_characters_to_image(characters).save("out/characters.png")


if __name__ == "__main__":
  main()
