"""自動檢查「所有」已登記的類別：各自的樣本都要通過驗證，卡片內容要對。
新增類別時只要補一個 tests/samples/<名稱>.json，這裡就會自動涵蓋它。"""
import json

import pytest

from core.cards import build_card
from core.registry import CATEGORIES, SAMPLES_DIR
from core.validate import validate_category_data


@pytest.mark.parametrize("name", sorted(CATEGORIES))
def test_category_sample(name):
    cat = CATEGORIES[name]
    sample = json.loads((SAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))
    data, conf = validate_category_data(cat, sample["model_output"]) if cat.analyze else (
        {"what_is": sample["model_output"]["what_is"]}, sample["model_output"]["confidence"])
    if cat.extra:
        data.update(cat.extra(dict(data)))
    card = build_card(cat, data, conf, record_id=7, nth_today=3)
    assert sample["expect_headline"] in card.title
    assert sample["expect_headline"] in card.summary  # 純文字版也要有內容
    assert all(value in card.summary for _, value in card.fields)
    assert "#7" in card.footer and "第 3 筆" in card.footer and conf in card.footer
    for key, value in sample.get("expect_extra", {}).items():
        assert data[key] == value
    assert ("判讀不一定準確" in card.footer) == (conf == "低")


def test_disaster_has_119_note():
    cat = CATEGORIES["disaster"]
    card = build_card(cat, {"disaster_type": "淹水", "severity": "輕微", "advice": "x"}, "高", 1, 1)
    assert "119" in card.footer
