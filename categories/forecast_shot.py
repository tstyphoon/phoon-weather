from core import Field, category
from services.units import beaufort


@category(
    name="forecast_shot", title="預報截圖", icon="📊",
    description="手機或網頁上的天氣預報截圖（含氣溫、降雨機率、風速等數字）",
    headline="預報截圖：{location}",
    fields=[
        Field("location", str, label="地點", required=False),
        Field("temp_min", float, label="最低溫（°C）", min=-60, max=60, required=False),
        Field("temp_max", float, label="最高溫（°C）", min=-60, max=60, required=False),
        Field("rain_prob", float, label="降雨機率（%）", min=0, max=100, required=False),
        Field("wind_speed", float, label="風速（m/s）", min=0, max=120, required=False,
              desc="單位一律換成 m/s；截圖若是 km/h，請除以 3.6"),
    ],
    extra_labels={"beaufort": "蒲福風級"},
)
def forecast_shot(data):
    """風速換算蒲福風級。"""
    wind = data.get("wind_speed")
    return {"beaufort": beaufort(wind)} if isinstance(wind, (int, float)) else {}
