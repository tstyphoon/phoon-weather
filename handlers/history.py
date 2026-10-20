import json

from core import command
from core.cards import record_summary
from core.registry import CATEGORIES


@command("history", description="列出自己最近的天氣紀錄（預設 5 筆，最多 20 筆）",
         usage="/history [筆數]")
async def history(ctx, n: int = 5):
    n = max(1, min(int(n), 20))
    rows = ctx.store.recent(ctx.user_id, n)
    if not rows:
        return "你還沒有任何天氣紀錄"
    lines = []
    for r in rows:
        when = r["created_at"][5:16].replace("-", "/")
        lines.append(f"`#{r['id']}` {when}　{record_summary(r['kind'], json.loads(r['data']), CATEGORIES)}")
    return "你最近的紀錄：\n" + "\n".join(lines) + "\n用 `/delete 編號` 可以刪除一筆"
