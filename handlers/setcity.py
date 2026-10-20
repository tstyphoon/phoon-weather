from core import command
from services.weather import WeatherError


@command("setcity", description="設定自己的預設城市", usage="/setcity 城市（例如 /setcity 新竹）")
async def setcity(ctx, arg: str):
    if not arg:
        return "請告訴我城市，例如：`/setcity 新竹`"
    try:
        place = await ctx.weather.resolve_place(arg)
    except WeatherError as e:
        return str(e)
    if place is None:
        return "找不到這個地點，原本的設定沒有改變"
    ctx.store.set_city(ctx.user_id, place.county or arg.strip())
    msg = f"已設定為：{place.name}"
    return msg + ("\n" + place.note if place.note else "")
