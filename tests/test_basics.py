import pytest

from core.config import ConfigError, load_config
from core.sanitize import neutralize_formula, neutralize_mentions, safe_filename_part
from core.validate import (ValidationError, extract_json, validate_category_data,
                           validate_classification)
from core.registry import CATEGORIES, Field, RegistryError, category, validate_all
from services.units import beaufort


def test_config_missing_names_only():
    with pytest.raises(ConfigError) as e:
        load_config("does-not-exist.env", environ={})
    assert "DISCORD_TOKEN" in str(e.value) and "CHANNEL_ID" in str(e.value)


def test_config_bad_channel_does_not_leak_token():
    with pytest.raises(ConfigError) as e:
        load_config("x.env", environ={"DISCORD_TOKEN": "SECRET123", "CHANNEL_ID": "abc"})
    assert "SECRET123" not in str(e.value)


def test_config_defaults_and_repr_hides_secrets():
    c = load_config("x.env", environ={"DISCORD_TOKEN": "SECRET123", "CHANNEL_ID": "42"})
    assert c.channel_id == 42 and c.claude_model == "haiku" and c.default_city == "台北"
    assert c.cwa_api_key is None and "SECRET123" not in repr(c)


@pytest.mark.parametrize("raw,bad", [("../../x", ".."), ("a/b\\c", "/"), ("12:30", ":"),
                                     ('a*?"<>|b', "*"), ("", None), ("....", None)])
def test_safe_filename(raw, bad):
    out = safe_filename_part(raw)
    assert out and (bad is None or bad not in out)
    assert "/" not in out and "\\" not in out and ".." not in out and ":" not in out


def test_safe_filename_length_and_control_chars():
    assert len(safe_filename_part("長" * 100)) <= 30
    assert "\x00" not in safe_filename_part("a\x00b\nc")


@pytest.mark.parametrize("t", ["=1+1", "+cmd", "-2", "@SUM(A1)"])
def test_formula_neutralized(t):
    assert neutralize_formula(t).startswith("'")
    assert neutralize_formula("正常文字") == "正常文字"


def test_mentions_neutralized():
    assert "@everyone" not in neutralize_mentions("hi @everyone @here")


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('好的：{"a": 1} 以上') == {"a": 1}
    for bad in ["", "沒有json", "{壞掉", "[1,2]"]:
        with pytest.raises(ValidationError):
            extract_json(bad)


def test_validate_numbers_ranges_choices():
    cat = CATEGORIES["forecast_shot"]
    ok = {"temp_min": "22", "temp_max": 28.5, "rain_prob": 60, "wind_speed": 6, "confidence": "高"}
    data, conf = validate_category_data(cat, ok)
    assert data["temp_min"] == 22.0 and conf == "高" and data["location"] is None
    for patch in [{"wind_speed": "很大"}, {"rain_prob": 150}, {"wind_speed": -1},
                  {"temp_min": True}, {"temp_max": float("nan")}, {"confidence": "超高"}]:
        with pytest.raises(ValidationError):
            validate_category_data(cat, {**ok, **patch})
    dis = CATEGORIES["disaster"]
    base = {"disaster_type": "淹水", "severity": "嚴重", "advice": "撤離", "confidence": "中"}
    validate_category_data(dis, base)
    with pytest.raises(ValidationError):
        validate_category_data(dis, {**base, "severity": "超級嚴重"})
    with pytest.raises(ValidationError):
        validate_category_data(dis, {k: v for k, v in base.items() if k != "advice"})


def test_classification_falls_back_to_non_weather():
    known = set(CATEGORIES)
    assert validate_classification({"category": "亂寫", "confidence": "高"}, known)["category"] == "non_weather"
    assert validate_classification({"category": "sky", "confidence": "怪"}, known)["confidence"] == "低"


def test_beaufort():
    assert [beaufort(x) for x in (0, 1, 3, 6.2, 12, 40)] == [0, 1, 2, 4, 6, 12]


def test_registry_rejects_bad_declarations():
    with pytest.raises(RegistryError):
        category(name="sky", title="x", icon="x", description="x", headline="{a}", fields=[])()
    category(name="_tmp_bad", title="x", icon="x", description="x", headline="{nope}",
             fields=[Field("a", str)])()
    try:
        with pytest.raises(RegistryError, match="不存在的欄位"):
            validate_all(require_samples=False)
    finally:
        CATEGORIES.pop("_tmp_bad")
