import json
import os
import struct

import lz10
from helper import DIR_UNPACKED_FILES, DIR_UNPACKED_IMAGE_FILES

file_list = ["arm9.bin"]
for file_name in os.listdir("original_files/overlay"):
  if file_name.endswith(".bin"):
    file_list.append(f"overlay/{file_name}")

original_sizes: dict[str, int] = {}

for file_name in file_list:
  with open(f"original_files/{file_name}", "rb") as reader:
    data = reader.read()

  file_name_without_ext = os.path.split(file_name)[-1].rsplit(".", 1)[0]
  output_path = f"{DIR_UNPACKED_FILES}/{DIR_UNPACKED_IMAGE_FILES}/{file_name_without_ext}"
  os.makedirs(output_path, exist_ok=True)

  for magic in [b"NCG\0", b"NCL\0", b"NCE\0", b"NSC\0"]:
    ext = magic.rstrip(b"\0").decode().lower()
    offset = data.find(magic)
    while offset > -1:
      try:
        output_file_name = f"{file_name_without_ext}_{offset - 5:08X}.{ext}"
        file_data = data[offset - 5 :]
        file_data, original_size = lz10.decompress_with_original_size(file_data)
        with open(f"{output_path}/{output_file_name}", "wb") as writer:
          writer.write(file_data)
        original_sizes[output_file_name] = original_size + (-original_size % 4)
      except Exception as e:
        if magic == b"NCL\0":
          output_file_name = f"{file_name_without_ext}_{offset:08X}_uncompressed.ncl"
          (color_count,) = struct.unpack_from("<I", data, offset + 4)
          file_data = data[offset : offset + color_count * 2 + 8]
          with open(f"{output_path}/{output_file_name}", "wb") as writer:
            writer.write(file_data)
          original_sizes[output_file_name] = color_count * 2 + 8
        elif magic == b"NCG\0":
          print(f"Not implemented: {magic}")
        elif magic == b"NCE\0":
          output_file_name = f"{file_name_without_ext}_{offset:08X}_uncompressed.nce"
          cell_count, unk1_count, unk2, unk_1_offset, unk_2_offset, unk3 = struct.unpack_from(f"<6H", data, offset + 4)
          file_data = data[offset : offset + unk_2_offset * 2 + unk1_count * 4]
          with open(f"{output_path}/{output_file_name}", "wb") as writer:
            writer.write(file_data)
          original_sizes[output_file_name] = unk_2_offset * 2 + unk1_count * 4
        elif magic == b"NSC\0":
          print(f"Not implemented: {magic}")
        else:
          print(f"Failed to decompress at offset {offset:08X} in file {file_name}: {e}")

      next_offset = data.find(magic, offset + 1)
      if next_offset == -1:
        break
      offset = next_offset

with open("files/original_sizes.json", "w", -1, "utf8", None, "\n") as writer:
  json.dump(original_sizes, writer, indent=2, ensure_ascii=False)
