import csv
import json
import logging
import os
import struct

import lz10
import nitrogfx.util
from helper import DIR_UNPACKED_FILES, DIR_UNPACKED_IMAGE_FILES
from PIL import Image

with open("files/original_sizes.json", "r", -1, "utf8") as reader:
  original_sizes: dict[str, int] = json.load(reader)

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

    image_path = f"files/images/{nsc_path.removesuffix('.nsc')}.png"
    if not os.path.exists(image_path):
      continue

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
    image = Image.open(image_path).convert("RGBA")
    x, y = 0, 0
    for i in range(tile_count):
      tile_image = image.crop((x, y, x + 8, y + 8))
      if tile_image.getchannel("A").getextrema()[0] == 0xFF:
        (temp,) = struct.unpack_from("<H", nsc_data, 0x0C + i * 2)
        tile_index = temp & 0x3FF
        pal_index = (temp >> 12) & 0xF
        flip_x = bool((temp >> 10) & 1)
        flip_y = bool((temp >> 11) & 1)
        if flip_x:
          tile_image = tile_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if flip_y:
          tile_image = tile_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        palette_image = Image.new("P", (8, 8))
        if bpp == 8:
          palette_image.putpalette(colors)
        else:
          palette_image.putpalette(colors[pal_index * 48 : (pal_index + 1) * 48])
        tile_image = tile_image.convert("RGB").quantize(palette=palette_image, dither=Image.Dither.NONE)
        tiles[tile_index] = tile_image.tobytes()

      x += 8
      if x >= width:
        x = 0
        y += 8

    if bpp == 8:
      ncg_data = ncg_data[:8] + b"".join(tiles)
    else:
      half_bytes = b"".join(tiles)
      temp = bytearray()
      for i in range(0, len(half_bytes), 2):
        temp.append(half_bytes[i] | (half_bytes[i + 1] << 4))
      ncg_data = ncg_data[:8] + bytes(temp)

    compressed_data = lz10.compress(ncg_data)
    compressed_size = len(compressed_data)

    if compressed_size > original_sizes[ncg_path]:
      logging.warning(
        f"Compressed size of {ncg_path} is larger than original size ({compressed_size} > {original_sizes[ncg_path]})"
      )
      continue

    bin_name, offset_hex = ncg_path.removesuffix(".ncg").rsplit("_", 1)
    offset = int(offset_hex, 16)
    if bin_name.startswith("overlay_"):
      output_dir = f"arm9_patch/{bin_name}/generated"
      offset += 0x21E6660
    else:
      output_dir = f"arm9_patch/generated"
      offset += 0x2000000
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/repl_{offset:07X}.bin"
    with open(output_path, "wb") as writer:
      writer.write(compressed_data)
