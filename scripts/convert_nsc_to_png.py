import csv
import os
import struct

import nitrogfx.util
from helper import DIR_UNPACKED_FILES, DIR_UNPACKED_IMAGE_FILES
from PIL import Image

with open("files/nsc_files.csv", "r", -1, "utf8") as reader:
  reader = csv.reader(reader)
  header = next(reader)
  for row in reader:
    row_dict = dict(zip(header, row))

    folder = f"{DIR_UNPACKED_FILES}/{DIR_UNPACKED_IMAGE_FILES}/{row_dict['folder']}"
    ncl_path = row_dict["NCL"]
    ncg_path = row_dict["NCG"]
    nsc_path = row_dict["NSC"]
    bpp = int(row_dict.get("bpp", 8))
    palette_offset = int(row_dict.get("palette_offset", 0))

    with open(f"{folder}/{ncl_path}", "rb") as reader:
      ncl_data = reader.read()

    assert ncl_data[:4] == b"NCL\0"
    (color_count,) = struct.unpack_from("<H", ncl_data, 4)

    colors = [0] * (palette_offset * 48)
    for c in struct.unpack_from(f"<{color_count}H", ncl_data, 8):
      color = nitrogfx.util.rgb555_to_color(c)
      colors.extend(color)

    with open(f"{folder}/{ncg_path}", "rb") as reader:
      ncg_data = reader.read()
    assert ncg_data[:4] == b"NCG\0"

    (encoded_size,) = struct.unpack_from("<I", ncg_data, 4)
    real_size = (encoded_size & 0xFFFF) * 0x20 * (2 ** ((encoded_size >> 16) & 1))
    if bpp == 8:
      tiles = [ncg_data[_ : _ + 64] for _ in range(8, real_size, 64)]
    elif bpp == 4:
      tiles = []
      for _ in range(8, real_size, 32):
        half_bytes = bytearray()
        for byte in ncg_data[_ : _ + 32]:
          half_bytes.append(byte & 0x0F)
          half_bytes.append(byte >> 4)
        tiles.append(bytes(half_bytes))
    else:
      raise ValueError(f"Unsupported bpp: {bpp}")

    with open(f"{folder}/{nsc_path}", "rb") as reader:
      nsc_data = reader.read()
    assert nsc_data[:4] == b"NSC\0"
    tile_count, unk, width_tile, height_tile = struct.unpack_from("<HHBB", nsc_data, 4)
    assert tile_count == width_tile * height_tile
    if bpp == 8:
      assert unk == 0x100
    else:
      assert unk == 0
    width = width_tile * 8
    height = height_tile * 8
    image = Image.new("RGBA", (width, height))
    x, y = 0, 0
    for i in range(tile_count):
      (temp,) = struct.unpack_from("<H", nsc_data, 0x0C + i * 2)
      tile_index = temp & 0x3FF
      pal_index = (temp >> 12) & 0xF
      flip_x = bool((temp >> 10) & 1)
      flip_y = bool((temp >> 11) & 1)
      tile = tiles[tile_index]
      tile_image = Image.frombytes("P", (8, 8), tile)
      if bpp == 8:
        tile_image.putpalette(colors)
      else:
        tile_image.putpalette(colors[pal_index * 48 : (pal_index + 1) * 48])
      tile_image = tile_image.convert("RGBA")
      if flip_x:
        tile_image = tile_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
      if flip_y:
        tile_image = tile_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
      image.paste(tile_image, (x, y))
      x += 8
      if x >= width:
        x = 0
        y += 8

    output_path = f"temp/images/{nsc_path.removesuffix('.nsc')}.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)
