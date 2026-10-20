from core import command
from core.registry import CATEGORIES


@command("today", description="今天自己傳過幾筆、各類別各幾筆", usage="/today")
async def today(ctx, _arg: str = ""):
    counts = ctx.store.today_counts(ctx.user_id)
    if not counts:
        return "今天你還沒有天氣紀錄"
    parts = []
    for kind, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        cat = CATEGORIES.get(kind)
        parts.append(f"{cat.icon + cat.title if cat else '💬天氣查詢'} {n}")
    lines = [f"今天 {sum(counts.values())} 筆：" + "、".join(parts)]

    winds = ctx.store.recent_wind(ctx.user_id)
    if winds:
        latest = winds[0]
        prev = next((w for w in winds[1:] if w["city"] == latest["city"]), None)
        if prev:
            diff = latest["wind_speed"] - prev["wind_speed"]
            lines.append(f"風速（{latest['city']}）與上一筆相比：{diff:+.1f} m/s")
    return "\n".join(lines)
