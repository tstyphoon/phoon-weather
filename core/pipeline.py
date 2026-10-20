"""圖片流程：分類 → 判讀 → 檢查 → 清洗 → 建檔存圖 → 回覆內容。

兩段防護寫在這個檔案：防護 3（檔名清洗）、防護 4（寫入與顯示的文字清洗）。
每一段的「關閉狀態」是它前面那幾行預設值；整段註解掉，就會回到沒有防護的行為。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from core import strings
from core.cards import CardData, build_card
from core.claude import ClaudeError
from core.context import Ctx
from core.registry import CATEGORIES, Category, RESERVED_CATEGORY
from core.sanitize import clean_text, neutralize_formula, neutralize_mentions, safe_filename_part
from core.store import now_local
from core.validate import (ValidationError, extract_json, validate_category_data,
                           validate_classification)

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 2  # 第一次加自動重試一次


class AnalysisFailed(Exception):
    """模型沒有給出合格的結果。對使用者顯示「判讀失敗」。"""


@dataclass
class Reply:
    text: str | None = None
    card: CardData | None = None


def classifier_prompt() -> str:
    lines = [f"- {c.name}：{c.description}" for c in CATEGORIES.values() if c.name != RESERVED_CATEGORY]
    lines.append(f"- {RESERVED_CATEGORY}：和天氣無關的圖片，或看不出是什麼天氣相關內容")
    return (
        "你是天氣圖片的分類器。看使用者給的圖片，從下列類別選一個最符合的：\n"
        + "\n".join(lines)
        + "\n\n不確定時選 non_weather，不要亂猜。只輸出一個 JSON 物件，不要有其他文字：\n"
        '{"category": "類別名稱", "confidence": "高|中|低", '
        '"label": "12 字內的簡短名稱", "what_is": "15 字內的名詞片語，只說圖片是什麼，不要寫成句子、不要加評論"}'
    )


def analyzer_prompt(cat: Category) -> str:
    specs = []
    for f in cat.fields:
        kind = {float: "數字", int: "整數", str: "文字"}[f.type]
        extra = []
        if f.min is not None or f.max is not None:
            extra.append(f"範圍 {f.min}~{f.max}")
        if f.choices:
            extra.append("只能是：" + "、".join(f.choices))
        if not f.required:
            extra.append("看不出來就填 null")
        specs.append(f'  "{f.name}": {kind}（{f.label or f.name}'
                     + (f"，{f.desc}" if f.desc else "") + (f"；{'；'.join(extra)}" if extra else "") + "）")
    return (
        f"這張圖片已被判定為「{cat.title}」：{cat.description}。\n"
        "請判讀圖片內容，只輸出一個 JSON 物件，不要有其他文字。欄位如下，"
        "數字只寫阿拉伯數字、不要帶單位：\n{\n" + ",\n".join(specs)
        + ',\n  "confidence": 文字（高、中或低，代表你有多確定）\n}'
    )


class Pipeline:
    def __init__(self, ctx_factory=None):
        self.ctx_factory = ctx_factory

    async def _ask(self, ctx: Ctx, system: str, image: bytes, media_type: str,
                   caption: str, validator):
        last = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                text = await ctx.claude.run(system, image=image, media_type=media_type,
                                            user_text=caption)
                return validator(extract_json(text))
            except (ClaudeError, ValidationError) as e:
                last = e
                log.warning("判讀第 %d 次失敗：%s", attempt + 1, e)
        raise AnalysisFailed(str(last))

    async def handle_image(self, ctx: Ctx, image: bytes, media_type: str, ext: str,
                           caption: str = "") -> Reply:
        caption = clean_text(caption, 300)
        known = set(CATEGORIES)
        cls = await self._ask(ctx, classifier_prompt(), image, media_type, caption,
                              lambda raw: validate_classification(raw, known))
        cat = CATEGORIES[cls["category"]]

        if cat.analyze:
            data, confidence = await self._ask(
                ctx, analyzer_prompt(cat), image, media_type, caption,
                lambda raw: validate_category_data(cat, raw))
        else:  # 例如非天氣：分類那一步已經夠了，省一次呼叫
            data, confidence = {"what_is": cls["what_is"]}, cls["confidence"]

        for k, v in list(data.items()):
            if isinstance(v, str):
                data[k] = clean_text(v, 200)
        if cat.extra:
            data.update(cat.extra(dict(data)))

        raw_label = clean_text(cls["label"] or cat.title, 40)
        note = caption or None

        # ---- 沒有防護 4 時的行為：文字原樣寫入與顯示 ----
        # ==== 防護 4：寫進紀錄與顯示的文字清洗 開始 ====
        data = {k: (neutralize_formula(neutralize_mentions(v)) if isinstance(v, str) else v)
                for k, v in data.items()}
        note = neutralize_formula(neutralize_mentions(note)) if note else None
        raw_label = neutralize_mentions(raw_label)
        # ==== 防護 4 結束 ====

        created = now_local()
        # ---- 沒有防護 3 時的行為：模型給的名稱直接放進檔名 ----
        label_part = raw_label
        # ==== 防護 3：模型回來的名稱拿去當檔名前先清洗 開始 ====
        label_part = safe_filename_part(raw_label)
        # ==== 防護 3 結束 ====
        filename = f"{created:%Y%m%d-%H%M%S}_{cat.name}_{label_part}.{ext}"
        path = ctx.store.save_image(filename, image)

        city = data.get("location") if isinstance(data.get("location"), str) else None
        stored = dict(data, confidence=confidence, label=raw_label)
        record_id = ctx.store.add_record(user_id=ctx.user_id, user_name=ctx.user_name,
                                         kind=cat.name, data=stored, city=city, note=note,
                                         image_path=path, created_at=created)
        if cat.name == RESERVED_CATEGORY:
            return Reply(text=strings.NOT_WEATHER.format(what=data["what_is"]))
        nth = ctx.store.today_count(ctx.user_id)
        return Reply(card=build_card(cat, data, confidence, record_id, nth))
