# Clean output folder
if (Test-Path -Path "out/" -PathType "Container") {
  Remove-Item -Recurse -Force "out/"
}
if (Test-Path -Path "temp/" -PathType "Container") {
  Remove-Item -Recurse -Force "temp/"
}

# Unpack/extract original files
if (-Not (Test-Path -Path "unpacked/arm9_bmg/000D4BF4.bmg" -PathType "Leaf")) {
  if (Test-Path -Path "unpacked/" -PathType "Container") {
    Remove-Item -Recurse -Force "unpacked/"
  }
  python scripts/extract_bmg_from_arm9.py
}

python scripts/generate_char_table.py
python scripts/create_font.py

python scripts/convert_json_to_bmg.py
python scripts/import_bmg_to_arm9.py
python scripts/import_nsc_from_png.py

python scripts/compile_arm9_patch.py
python scripts/create_xdelta.py

python scripts/edit_banner.py

Copy-Item -LiteralPath "files/md5.txt" -Destination "out/md5.txt" -Force
Copy-Item -LiteralPath "files/metadata.json" -Destination "out/metadata.json" -Force
Copy-Item -LiteralPath "files/README.md" -Destination "out/README.md" -Force

Compress-Archive -Path "out/xdelta", "out/banner.bin", "out/md5.txt", "out/metadata.json", "out/README.md" -DestinationPath "patch-ds.zip" -Force
Move-Item -Path "patch-ds.zip" -Destination "out/patch-ds.xzp" -Force
