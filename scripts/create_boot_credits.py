import os
import struct

import lz10
import nitrogfx.c_ext.tile
import nitrogfx.util
from PIL import Image


def create_boot_credits(image_path: str, output_root: str):
  with Image.open(image_path) as image:
    if image.format != "PNG" or image.size != (256, 192):
      raise ValueError("Boot credits must be a 256x192 PNG")
    image = image.convert("RGBA")

  if image.getchannel("A").getextrema() != (255, 255):
    raise ValueError("Boot credits must be fully opaque")

  image = image.convert("RGB").quantize(colors=16, dither=Image.Dither.NONE).convert("RGB")
  colors = [nitrogfx.util.color_to_rgb555(pixel[:3]) for pixel in image.getdata()]
  palette = list(dict.fromkeys(colors))

  indices = {color: index for index, color in enumerate(palette)}
  indexed = Image.new("P", image.size)
  indexed.putdata([indices[color] for color in colors])
  tiles = bytearray()
  for y in range(0, 192, 8):
    for x in range(0, 256, 8):
      tiles.extend(nitrogfx.c_ext.tile._8bpp_to_4bpp(indexed.crop((x, y, x + 8, y + 8)).tobytes()))

  background = tiles + bytes(0x8000 - len(tiles))
  background.extend(struct.pack("<1024H", *range(768), *([0] * 256)))
  palette.extend([0] * (16 - len(palette)))
  os.makedirs(output_root, exist_ok=True)
  with open(f"{output_root}/boot_credits.lz", "wb") as writer:
    writer.write(lz10.compress(background))
  with open(f"{output_root}/boot_credits.pal", "wb") as writer:
    writer.write(struct.pack("<16H", *palette))
