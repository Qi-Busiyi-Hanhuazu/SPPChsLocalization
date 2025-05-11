import json
import os
import re
from typing import TypedDict

import ndspy.fnt

DIR_TEXT_FILES = "texts"
DIR_ORIGINAL_FILES = "original_files"
DIR_OUT = "out"
DIR_ARM9_PATCH = "arm9_patch"

DIR_DATA = "data/data"
DIR_FONT_FILES = "files/fonts"
DIR_UNPACKED_FILES = "unpacked"
DIR_TEMP_IMPORT = "temp/import"
DIR_TEMP_OUT = "temp/out"

DIR_UNPACKED_BMG_FILES = "arm9_bmg"
DIR_UNPACKED_IMAGE_FILES = "image_files"
DIR_ARM9_PATCH_GENERATED = "generated"


OLD_CHAR_TABLE_PATH = "files/char_table.json"
CHAR_TABLE_PATH = "out/char_table.json"
BANNER_PATH = "original_files/banner.bin"
BANNER_OUT_PATH = "out/banner.bin"
SYMBOL_OUT_PATH = "out/symbols.txt"

TRASH_PATTERN = re.compile(r"^(?:[\-\. \n]|\[[^\[\]]+\])*$|.*(?:てすと|テスト).*", re.DOTALL)
CONTROL_PATTERN = re.compile(r"\^[0-9A-Za-z]|%[ds]|~[CFcf][0-9\-]+")
KANA_PATTERN = re.compile(r"[\u3040-\u309F\u30A0-\u30FF]+")

CHINESE_TO_JAPANESE = {
  " ": "　",
  "·": "・",
  "—": "一",
  "～": "〜",
}
FONT_REPLACE_CHAR = {}
GENERATED_CHARACTERS = "，《》"


class TranslationItem(TypedDict):
  index: int
  key: str
  original: str
  translation: str
  suffix: str
  trash: bool
  untranslated: bool
  offset: int
  max_length: int


def load_translation_dict(path: str) -> dict[str, str]:
  with open(path, "r", -1, "utf8") as reader:
    translation_list: list[TranslationItem] = json.load(reader)

  translations = {}
  for item_dict in translation_list:
    if item_dict.get("trash", False):
      continue
    if item_dict.get("untranslated", False) and item_dict["original"] == item_dict["translation"]:
      continue
    translations[item_dict["key"]] = item_dict["translation"]

  return translations


def load_translation_items(path: str) -> list[TranslationItem]:
  with open(path, "r", -1, "utf8") as reader:
    translation_list = json.load(reader)

  return translation_list


def get_used_characters(json_root: str) -> set[str]:
  characters = set()
  for root, dirs, files in os.walk(json_root):
    for file_name in files:
      if not file_name.endswith(".json"):
        continue

      translations = load_translation_dict(f"{root}/{file_name}")

      for key, content in translations.items():
        content = CONTROL_PATTERN.sub("", content).replace("\n", "")
        if KANA_PATTERN.search(content):
          pass

        for k, v in CHINESE_TO_JAPANESE.items():
          content = content.replace(k, v)

        for char in content:
          characters.add(char)

  return characters


def get_used_characters_by_usage(json_root: str) -> list[str]:
  character_dict = {}
  for root, dirs, files in os.walk(json_root):
    for file_name in files:
      if not file_name.endswith(".json"):
        continue

      translations = load_translation_dict(f"{root}/{file_name}")

      for key, content in translations.items():
        content = CONTROL_PATTERN.sub("", content).replace("\n", "")
        if KANA_PATTERN.search(content):
          pass

        for k, v in CHINESE_TO_JAPANESE.items():
          content = content.replace(k, v)

        for char in content:
          character_dict[char] = character_dict.get(char, 0) + 1

  characters = sorted(character_dict.keys(), key=lambda x: character_dict[x], reverse=True)
  return characters


def convert_chs_characters_to_ja(char: str) -> str:
  char = CHINESE_TO_JAPANESE.get(char, char)
  if char in "0123456789":
    char = chr(ord(char) - ord("0") + ord("０"))
  elif char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    char = chr(ord(char) - ord("A") + ord("Ａ"))
  elif char in "abcdefghijklmnopqrstuvwxyz":
    char = chr(ord(char) - ord("a") + ord("ａ"))
  return char


def enumrate_narc_files(folder: ndspy.fnt.Folder, prefix: str = ""):
  for i, file_name in enumerate(folder.files):
    yield i + folder.firstID, prefix + file_name
  for folder_name, folder in folder.folders:
    yield from enumrate_narc_files(folder, prefix + folder_name + "/")
