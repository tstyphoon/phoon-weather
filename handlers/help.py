from core import command
from core.registry import CATEGORIES, COMMANDS, RESERVED_CATEGORY


@command("help", description="列出所有功能與用法", usage="/help")
async def help_(ctx, _arg: str = ""):
    lines = ["**天氣助理用法**", "", "📷 直接傳天氣相關的圖片（不用 @bot），我會判讀並建檔。目前看得懂："]
    lines += [f"　{c.icon} {c.title}：{c.description}" for c in CATEGORIES.values()
              if c.name != RESERVED_CATEGORY]
    lines += ["", "💬 問天氣：@我 加上問題，例如「@天氣助理 台北明天會下雨嗎」（現在、今天、明天、後天）", "",
              "指令："]
    lines += [f"　`{c.usage}`　{c.description}" for c in COMMANDS.values()]
    return "\n".join(lines)
