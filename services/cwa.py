"""中央氣象署開放資料。需要 CWA_API_KEY。

用到三個資料集：
- F-C0032-001：各縣市 36 小時天氣預報（天氣現象、降雨機率、最低與最高溫）
- O-A0003-001：現在天氣觀測報告（各測站即時氣溫、風速、雨量）
- W-C0033-001：各縣市目前的天氣警特報
"""
from __future__ import annotations

import httpx

BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"


class CwaError(Exception):
    pass


async def _get(client: httpx.AsyncClient, key: str, dataset: str, **params) -> dict:
    try:
        r = await client.get(BASE + dataset,
                             params={"Authorization": key, "format": "JSON", **params})
        r.raise_for_status()
        j = r.json()
    except (httpx.HTTPError, ValueError) as e:
        # 錯誤訊息不能帶出網址，因為網址裡有授權碼
        raise CwaError(type(e).__name__) from None
    if str(j.get("success")).lower() not in ("true", "1"):
        raise CwaError("氣象署回應失敗")
    return j


async def forecast_36h(client, key: str, county: str) -> list[dict]:
    """回傳依時間排序的時段：{start, end, wx, pop, min_t, max_t}。"""
    j = await _get(client, key, "F-C0032-001", locationName=county)
    try:
        loc = j["records"]["location"][0]
        el = {e["elementName"]: e["time"] for e in loc["weatherElement"]}
        slots = []
        for i, t in enumerate(el["Wx"]):
            slots.append({
                "start": t["startTime"], "end": t["endTime"],
                "wx": t["parameter"]["parameterName"],
                "pop": float(el["PoP"][i]["parameter"]["parameterName"]),
                "min_t": float(el["MinT"][i]["parameter"]["parameterName"]),
                "max_t": float(el["MaxT"][i]["parameter"]["parameterName"]),
            })
        return slots
    except (KeyError, IndexError, ValueError):
        raise CwaError("預報格式不符") from None


async def observation(client, key: str, county: str) -> dict | None:
    """該縣市第一個有有效資料的測站即時觀測。沒有回傳 None。"""
    j = await _get(client, key, "O-A0003-001")
    for s in j.get("records", {}).get("Station", []):
        if s.get("GeoInfo", {}).get("CountyName") != county:
            continue
        w = s.get("WeatherElement", {})
        try:
            temp, wind = float(w["AirTemperature"]), float(w["WindSpeed"])
        except (KeyError, ValueError):
            continue
        if temp < -50 or wind < 0:  # 氣象署用 -99 表示沒資料
            continue
        try:
            rain = max(float(w.get("Now", {}).get("Precipitation", 0)), 0.0)
        except ValueError:
            rain = 0.0
        return {"station": s.get("StationName", ""), "temp": temp,
                "wind_speed": wind, "rain_mm": rain, "weather": w.get("Weather", "")}
    return None


async def warnings(client, key: str, county: str) -> list[str]:
    """該縣市目前生效中的警特報，例如「豪雨 特報」。"""
    j = await _get(client, key, "W-C0033-001")
    out = []
    for loc in j.get("records", {}).get("location", []):
        if loc.get("locationName") != county:
            continue
        for h in loc.get("hazardConditions", {}).get("hazards", []):
            info = h.get("info", {})
            out.append(f"{info.get('phenomena', '')}{info.get('significance', '')}".strip())
    return [w for w in dict.fromkeys(out) if w]
