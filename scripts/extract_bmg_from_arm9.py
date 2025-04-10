import os
import struct
from helper import DIR_ORIGINAL_FILES, DIR_UNPACKED_FILES, DIR_UNPACKED_BMG_FILES

BMG_MAGIC_HEADER = b"MESGbmg1"
TRASH_OFFSET = (0xDA4F4, 0xDD9D4, 0xE88B4)


def extract_bmg_from_arm9(input_path: str, output_root: str):
  with open(input_path, "rb") as reader:
    data = reader.read()

  offset = data.find(BMG_MAGIC_HEADER)
  while offset != -1:
    (file_size,) = struct.unpack(">I", data[offset + 0x08 : offset + 0x0C])
    if offset not in TRASH_OFFSET:
      file_data = data[offset : offset + file_size]
      path = f"{output_root}/{offset:08X}.bmg"
      os.makedirs(os.path.dirname(path), exist_ok=True)
      with open(path, "wb") as writer:
        writer.write(file_data)

    offset = data.find(BMG_MAGIC_HEADER, offset + file_size)


if __name__ == "__main__":
  extract_bmg_from_arm9(f"{DIR_ORIGINAL_FILES}/arm9.bin", f"{DIR_UNPACKED_FILES}/{DIR_UNPACKED_BMG_FILES}")
