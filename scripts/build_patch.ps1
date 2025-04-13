# Clean output folder
if (Test-Path -Path "out\" -PathType "Container") {
  Remove-Item -Recurse -Force "out\"
}
if (Test-Path -Path "temp\" -PathType "Container") {
  Remove-Item -Recurse -Force "temp\"
}

# Unpack/extract original files
if (-Not (Test-Path -Path "unpacked\arm9_bmg\000D4BF4.bmg" -PathType "Leaf")) {
  if (Test-Path -Path "unpacked\" -PathType "Container") {
    Remove-Item -Recurse -Force "unpacked\"
  }
  python scripts\extract_bmg_from_arm9.py
}

python scripts\generate_char_table.py
python scripts\create_font.py

python scripts\convert_json_to_bmg.py
python scripts\import_bmg_to_arm9.py

python scripts\compile_arm9_patch.py
python scripts\create_xdelta.py

python scripts\edit_banner.py

New-Item -ItemType Directory -Path "out\overlay\" -Force | Out-Null
Copy-Item -Path "maintenance\images\title\overlay_0019.bin" -Destination "out\overlay\overlay_0019.bin" -Force

New-Item -ItemType Directory -Path "out\data\" -Force | Out-Null
Compress-Archive -Path "out/data/", "out/xdelta/", "out/overlay", "out/banner.bin" -Destination "patch-ds.zip" -Force
Move-Item -Path "patch-ds.zip" -Destination "out/patch-ds.xzp" -Force
