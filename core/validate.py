"""檢查模型回傳的東西。不相信模型：格式、型別、範圍、選項都要對才放行。"""
from __future__ import annotations

import json
import re

from core.registry import Category, Field

CONFIDENCE = ("高", "中", "低")


class ValidationError(Exception):
    pass


def extract_json(text: str) -> dict:
    """從模型回傳的文字取出第一個 JSON 物件。找不到或不合法就丟 ValidationError。"""
    if not isinstance(text, str):
        raise ValidationError("回傳不是文字")
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    start = text.find("{")
    if start < 0:
        raise ValidationError("找不到 JSON")
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as e:
        raise ValidationError(f"不是合法的 JSON：{e.msg}") from None
    if not isinstance(obj, dict):
        raise ValidationError("JSON 最外層必須是物件")
    return obj


def _check_field(f: Field, raw):
    if raw is None or raw == "":
        if f.required:
            raise ValidationError(f"缺少欄位 {f.name}")
        return None
    if f.type in (int, float):
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            raise ValidationError(f"{f.name} 必須是數字")
        try:
            val = f.type(float(raw)) if f.type is int else float(raw)
        except (ValueError, OverflowError):
            raise ValidationError(f"{f.name} 必須是數字") from None
        if val != val or val in (float("inf"), float("-inf")):
            raise ValidationError(f"{f.name} 必須是有限的數字")
        if f.min is not None and val < f.min:
            raise ValidationError(f"{f.name} 小於下限 {f.min}")
        if f.max is not None and val > f.max:
            raise ValidationError(f"{f.name} 超過上限 {f.max}")
        return val
    if isinstance(raw, (dict, list)):
        raise ValidationError(f"{f.name} 必須是文字")
    val = str(raw).strip()
    if f.choices and val not in f.choices:
        raise ValidationError(f"{f.name} 必須是 {f.choices} 之一")
    return val


def validate_category_data(cat: Category, raw: dict) -> tuple[dict, str]:
    """驗證某類別的判讀結果，回傳 (欄位資料, 信心)。"""
    conf = str(raw.get("confidence", "")).strip()
    if conf not in CONFIDENCE:
        raise ValidationError("confidence 必須是 高 / 中 / 低")
    data = {f.name: _check_field(f, raw.get(f.name)) for f in cat.fields}
    return data, conf


def validate_classification(raw: dict, known: set[str]) -> dict:
    """分類結果。分不出來或類別不認識，一律歸為非天氣，不亂猜。"""
    name = str(raw.get("category", "")).strip()
    conf = str(raw.get("confidence", "")).strip()
    if conf not in CONFIDENCE:
        conf = "低"
    if name not in known:
        name = "non_weather"
    return {
        "category": name,
        "confidence": conf,
        "label": str(raw.get("label", "")).strip()[:40],
        "what_is": str(raw.get("what_is", "")).strip()[:80] or "無法辨識的東西",
    }
