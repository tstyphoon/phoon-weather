"""@bot 文字問天氣。第一行直接回答問題，下面附固定摘要。"""
import re

from core import strings, text_intent
from core.sanitize import clean_text, neutralize_formula
from services.units import beaufort
from services.places import find_county
from services.weather import WeatherError

_UNSUPPORTED = re.compile(r"大後天|下週|下周|下星期|下禮拜|下個?禮拜|週末|周末|本週|這週|一週|一周|七天|7天|[4-9]天後|[四五六七八九]天後")
_LATIN_PLACE = re.compile(r"[A-Za-z][A-Za-z .'\-]{2,}[A-Za-z]")


def parse_day(text: str):
    """回傳 'now' / 0 / 1 / 2 / None（None：超出範圍）。沒提到時間就當作今天。"""
    if _UNSUPPORTED.search(text):
        return None
    if "後天" in text:
        return 2
    if re.search(r"明天|明日|明早|明晚", text):
        return 1
    if re.search(r"現在|目前|現況|此刻|馬上", text):
        return "now"
    return 0


def _answer(rep, text: str) -> str:
    where, day = rep.place.name, rep.day_label
    if re.search(r"雨|傘", text):
        if rep.day == "now" and rep.rain_mm is not None:
            now = f"{where}現在" + ("正在下雨" if rep.rain_mm > 0 else "沒有下雨")
            return now + (f"（今天降雨機率 {rep.rain_prob:g}%）" if rep.rain_prob is not None else "")
        if rep.rain_prob is not None:
            p = rep.rain_prob
            tip = "建議帶傘" if p >= 50 else "不太需要帶傘" if p < 30 else "可以帶把傘以防萬一"
            return f"{where}{day}降雨機率 {p:g}%，{tip}"
    if re.search(r"冷|熱|溫|幾度|穿", text):
        if rep.temp_now is not None and rep.day == "now":
            return f"{where}現在氣溫約 {rep.temp_now:g}°C"
        if rep.temp_min is not None and rep.temp_max is not None:
            return f"{where}{day}氣溫約 {rep.temp_min:g}～{rep.temp_max:g}°C"
        if rep.temp_now is not None:
            return f"{where}現在氣溫約 {rep.temp_now:g}°C"
    if re.search(r"風|颱", text) and rep.wind_speed is not None:
        return f"{where}{day}風速約 {rep.wind_speed:g} m/s（蒲福 {beaufort(rep.wind_speed)} 級）"
    return f"{where}{day}" + (f"：{rep.summary}" if rep.summary else "的天氣如下")


def _summary(rep) -> list[str]:
    lines = []
    if rep.temp_now is not None:
        lines.append(f"目前氣溫：{rep.temp_now:g}°C")
    if rep.temp_min is not None and rep.temp_max is not None:
        lines.append(f"{'今天' if rep.day == 'now' else rep.day_label}氣溫：{rep.temp_min:g}～{rep.temp_max:g}°C")
    if rep.rain_prob is not None:
        lines.append(f"降雨機率：{rep.rain_prob:g}%")
    elif rep.rain_mm is not None:
        lines.append(f"目前雨量：{rep.rain_mm:g} mm")
    if rep.wind_speed is not None:
        lines.append(f"風速：{rep.wind_speed:g} m/s（蒲福 {beaufort(rep.wind_speed)} 級）")
    return lines


@text_intent("weather_query")
async def weather_query(ctx, text: str):
    text = clean_text(text, 200)
    if not text:
        return "想問天氣嗎？例如：@我 台北明天會下雨嗎"
    day = parse_day(text)
    if day is None:
        return strings.ONLY_THREE_DAYS

    try:
        place = await _find_place(ctx, text)
        rep = await ctx.weather.report(place, day)
    except WeatherError:
        return strings.WEATHER_DOWN

    out = [_answer(rep, text), ""] + _summary(rep)
    if rep.warnings:
        out.append("⚠️ 目前警特報：" + "、".join(rep.warnings))
    out.append(f"資料來源：{rep.source}")
    if not ctx.has_city:
        out.append(strings.NO_CITY_HINT)

    ctx.store.add_record(
        user_id=ctx.user_id, user_name=ctx.user_name, kind="text_query", city=place.name,
        data={"question": neutralize_formula(text), "day": rep.day_label, "location": place.name,
              "temp_min": rep.temp_min, "temp_max": rep.temp_max, "rain_prob": rep.rain_prob,
              "wind_speed": rep.wind_speed})
    return "\n".join(out)


async def _find_place(ctx, text: str):
    """問句裡有台灣縣市或英文地名就用它；沒有就用這位使用者設定的城市。"""
    candidates = []
    if find_county(text):
        candidates.append(text)
    latin = _LATIN_PLACE.search(text)
    if latin:
        candidates.append(latin.group(0))
    candidates += [ctx.city, "台北"]
    for name in candidates:
        place = await ctx.weather.resolve_place(name)
        if place:
            return place
    raise WeatherError("找不到地點")
