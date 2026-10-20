"""清洗用的小工具。使用的位置由 pipeline 的「防護 3、4」區塊決定。"""
from __future__ import annotations

import re
import unicodedata

_FORBIDDEN_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ZWSP = "​"


def safe_filename_part(text: str, max_len: int = 30) -> str:
    """把任意文字變成可以放進檔名的一小段：不含路徑符號、冒號、控制字元。"""
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("..", "_")
    text = _FORBIDDEN_FILENAME.sub("_", text)
    text = re.sub(r"\s+", "_", text).strip("._ ")
    text = text[:max_len].strip("._ ")
    return text or "x"


def neutralize_formula(text: str) -> str:
    """以 = + - @ 開頭的文字前面加單引號，之後匯出到 Excel 才不會被當公式。"""
    if text and text[0] in "=+-@\t\r":
        return "'" + text
    return text


def neutralize_mentions(text: str) -> str:
    """讓 @everyone、@here、@某人 不會真的通知別人。"""
    return text.replace("@", "@" + _ZWSP)


def clean_text(text: object, max_len: int = 300) -> str:
    """移除控制字元、限制長度。（公式與提及的處理另外做，方便各自開關。）"""
    text = _CONTROL.sub("", str(text)).strip()
    return text[:max_len]
