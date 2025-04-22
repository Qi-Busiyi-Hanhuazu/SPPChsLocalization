import logging
import os
import struct

from extract_bmg_from_arm9 import BMG_MAGIC_HEADER
from helper import (
  DIR_ARM9_PATCH,
  DIR_ARM9_PATCH_ADDITIONAL,
  DIR_ORIGINAL_FILES,
  DIR_TEMP_IMPORT,
  DIR_UNPACKED_BMG_FILES,
)


def import_bmg_to_arm9(input_path: str, bmg_root: str, output_root: str):
  with open(input_path, "rb") as reader:
    data = reader.read()

  offset = data.find(BMG_MAGIC_HEADER)
  while offset != -1:
    (file_size,) = struct.unpack(">I", data[offset + 0x08 : offset + 0x0C])
    bmg_path = f"{bmg_root}/{offset:08X}.bmg"
    if os.path.exists(bmg_path):
      with open(bmg_path, "rb") as reader:
        bmg_data = reader.read()
      new_file_size = len(bmg_data)
      if new_file_size > file_size:
        logging.warning(f"File size mismatch: {bmg_path} ({new_file_size} > {file_size})")
      elif new_file_size < file_size:
        bmg_data += b"\x00" * (file_size - new_file_size)

      output_path = f"{output_root}/repl_{offset + 0x2000000:07X}.bin"
      os.makedirs(os.path.dirname(output_path), exist_ok=True)
      with open(output_path, "wb") as writer:
        writer.write(bmg_data)

    offset = data.find(BMG_MAGIC_HEADER, offset + file_size)


if __name__ == "__main__":
  import_bmg_to_arm9(
    f"{DIR_ORIGINAL_FILES}/arm9.bin",
    f"{DIR_TEMP_IMPORT}/{DIR_UNPACKED_BMG_FILES}",
    f"{DIR_ARM9_PATCH}/{DIR_ARM9_PATCH_ADDITIONAL}",
  )
