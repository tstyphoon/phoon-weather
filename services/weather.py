"""天氣資料的統一入口。

台灣地點優先用中央氣象署（官方預報、即時觀測、警特報）；
海外地點，或氣象署沒設金鑰／查不到／沒回應時，退回 Open-Meteo。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

import httpx

from core.store import now_local
from services import cwa, open_meteo
from services.places import TAIWAN_COUNTIES, find_county

log = logging.getLogger(__name__)

DAY_LABELS = {"now": "現在", 0: "今天", 1: "明天", 2: "後天"}


class WeatherError(Exception):
    """所有資料來源都失敗。"""


@dataclass
class Place:
    name: str
    lat: float
    lon: float
    county: str | None = None  # 台灣地點才有：氣象署的縣市名稱
    note: str = ""


@dataclass
class WeatherReport:
    place: Place
    day: str | int
    source: str  # "中央氣象署" / "Open-Meteo"
    summary: str = ""
    temp_min: float | None = None
    temp_max: float | None = None
    temp_now: float | None = None
    rain_prob: float | None = None
    rain_mm: float | None = None
    wind_speed: float | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def day_label(self) -> str:
        return DAY_LABELS[self.day]


class WeatherService:
    def __init__(self, cwa_key: str | None, client: httpx.AsyncClient | None = None):
        self.cwa_key = cwa_key
        self.client = client or httpx.AsyncClient(timeout=15.0)

    async def resolve_place(self, text: str) -> Place | None:
        """地名 -> Place。台灣縣市優先；其他地名用 Open-Meteo 查座標。找不到回傳 None。"""
        county = find_county(text)
        if county:
            lat, lon = TAIWAN_COUNTIES[county]
            note = ""
            if county in ("新竹市", "嘉義市") and county[:-1] + "縣" not in text and county not in text:
                note = f"若不是你要的，請輸入完整名稱，例如「{county[:-1]}縣」"
            return Place(county, lat, lon, county, note)
        try:
            g = await open_meteo.geocode(self.client, text.strip())
        except open_meteo.OpenMeteoError:
            raise WeatherError("地名查詢服務暫時無法使用") from None
        if not g:
            return None
        name = "，".join(x for x in (g["name"], g["admin1"], g["country"]) if x)
        return Place(name, g["lat"], g["lon"], None,
                     "若不是你要的，請輸入更完整的地名，例如「Springfield, Illinois」")

    async def report(self, place: Place, day: str | int) -> WeatherReport:
        if place.county and self.cwa_key:
            try:
                return await self._from_cwa(place, day)
            except cwa.CwaError as e:
                log.warning("氣象署查詢失敗（%s），改用 Open-Meteo", e)
        return await self._from_open_meteo(place, day)

    # ---- 氣象署 ----
    async def _from_cwa(self, place: Place, day) -> WeatherReport:
        c, key, county = self.client, self.cwa_key, place.county
        rep = WeatherReport(place, day, "中央氣象署")
        try:
            rep.warnings = await cwa.warnings(c, key, county)
        except cwa.CwaError:
            rep.warnings = []

        slots = await cwa.forecast_36h(c, key, county)
        target_idx = 0 if day == "now" else day
        date = (now_local() + timedelta(days=target_idx)).strftime("%Y-%m-%d")
        todays = [s for s in slots if s["start"].startswith(date)]
        if todays:
            rep.temp_min = min(s["min_t"] for s in todays)
            rep.temp_max = max(s["max_t"] for s in todays)
            rep.rain_prob = max(s["pop"] for s in todays)
            rep.summary = todays[0]["wx"]
        elif day != "now":
            # 36 小時預報涵蓋不到（例如後天）：溫度、降雨機率改用 Open-Meteo
            om = await self._open_meteo_or_none(place, day)
            if om is None:
                raise cwa.CwaError("36 小時預報涵蓋不到，備援也失敗")
            rep.temp_min, rep.temp_max = om["temp_min"], om["temp_max"]
            rep.rain_prob, rep.wind_speed = om["rain_prob"], om["wind_speed"]
            rep.source = "中央氣象署、Open-Meteo"
            return rep

        if day == "now":
            obs = await cwa.observation(c, key, county)
            if obs:
                rep.temp_now, rep.wind_speed, rep.rain_mm = obs["temp"], obs["wind_speed"], obs["rain_mm"]
                rep.summary = obs["weather"] or rep.summary
                return rep
        # 預報沒有風速：風速用 Open-Meteo 補
        om = await self._open_meteo_or_none(place, 0 if day == "now" else day)
        if om:
            rep.wind_speed = om["now"]["wind_speed"] if day == "now" else om["wind_speed"]
            if day == "now":
                rep.temp_now = om["now"]["temp"]
            rep.source = "中央氣象署、Open-Meteo"
        return rep

    # ---- Open-Meteo ----
    async def _open_meteo_or_none(self, place: Place, offset: int):
        try:
            return await open_meteo.forecast(self.client, place.lat, place.lon, offset)
        except open_meteo.OpenMeteoError as e:
            log.warning("Open-Meteo 查詢失敗：%s", e)
            return None

    async def _from_open_meteo(self, place: Place, day) -> WeatherReport:
        try:
            om = await open_meteo.forecast(self.client, place.lat, place.lon,
                                           0 if day == "now" else day)
        except open_meteo.OpenMeteoError:
            raise WeatherError("所有天氣資料來源都沒有回應") from None
        rep = WeatherReport(place, day, "Open-Meteo", temp_min=om["temp_min"],
                            temp_max=om["temp_max"], rain_prob=om["rain_prob"],
                            wind_speed=om["wind_speed"])
        if day == "now":
            rep.temp_now, rep.wind_speed = om["now"]["temp"], om["now"]["wind_speed"]
            rep.rain_mm = om["now"]["rain_mm"]
        return rep
