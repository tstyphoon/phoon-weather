from core import command


@command("delete", description="刪除自己的一筆紀錄（圖片一併刪除）", usage="/delete 編號")
async def delete(ctx, record_id: int = 0):
    if not record_id:
        return "請給編號，例如：`/delete 12`（編號在 `/history` 查得到）"
    if ctx.store.delete_record(ctx.user_id, record_id):
        return f"已刪除第 {record_id} 筆"
    return f"找不到第 {record_id} 筆（只能刪除自己的紀錄）"
