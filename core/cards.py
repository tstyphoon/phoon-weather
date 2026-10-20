"""組出回覆的卡片內容（與 Discord 無關，方便測試）。

類別自己宣告圖示、結論、欄位；頁尾（紀錄編號、信心、今天第 N 筆、免責）由這裡統一加。
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from core import strings
from core.registry import Category

COLORS = {"sky": 0x4DA6FF, "radar": 0x7E57C2, "disaster": 0xE53935, "forecast_shot": 0x26A69A}
DEFAULT_COLOR = 0x78909C


@dataclass
class CardData:
    title: str
    fields: list[tuple[str, str]] = field(default_factory=list)
    footer: str = ""
    color: int = DEFAULT_COLOR


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def build_card(cat: Category, data: dict, confidence: str, record_id: int, nth_today: int) -> CardData:
    shown = defaultdict(lambda: "不明", {k: _fmt(v) for k, v in data.items() if v is not None})
    headline = cat.headline.format_map(shown)

    fields = [(f.label or f.name, _fmt(data[f.name])) for f in cat.fields
              if data.get(f.name) is not None]
    fields += [(label, _fmt(data[key])) for key, label in cat.extra_labels.items()
               if data.get(key) is not None]

    lines = [f"紀錄編號 #{record_id}　信心：{confidence}　今天第 {nth_today} 筆"]
    if confidence == "低":
        lines.append(strings.LOW_CONFIDENCE)
    lines += cat.footer_notes

    return CardData(title=f"{cat.icon} {headline}", fields=fields, footer="\n".join(lines),
                    color=COLORS.get(cat.name, DEFAULT_COLOR))


def record_summary(kind: str, data: dict, cats: dict[str, Category]) -> str:
    """把一筆紀錄壓成一行文字，給 /history 用。"""
    cat = cats.get(kind)
    if cat:
        shown = defaultdict(lambda: "不明", {k: _fmt(v) for k, v in data.items() if v is not None})
        return f"{cat.icon} {cat.headline.format_map(shown)}"
    if kind == "text_query":
        return f"💬 {data.get('location', '')}{data.get('day', '')} 查詢：{data.get('question', '')[:20]}"
    return kind
