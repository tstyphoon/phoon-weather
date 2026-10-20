# phoon-weather

在我電腦上執行的 Discord 天氣情報助理：頻道裡有人傳天氣相關圖片或 @bot 問天氣，它用 `claude -p` 判讀或查詢 Open-Meteo，建檔後回覆上傳者。

## 工作規則

- 開始任何工作前，先讀 `docs/architecture.md`（需求在 `requirements.md`）。
- 四段防護要各自用清楚的註解標起來，格式為「防護 N 開始」與「防護 N 結束」（N 為 1 到 4），一開始**全部開啟**。防護都放在 `core/`，不要在各功能裡個別處理：
  1. `claude -p` 不給任何工具，圖片以資料傳入，在空的暫存資料夾執行，不帶金鑰
  2. 使用者送進來的文字與檔案只當資料，不混進給模型的指令
  3. 要拿去當檔名的字先清洗（`/`、`\`、`..`、`:` 等）
  4. 檢查模型回傳；寫入的文字以 `=`、`+`、`-`、`@` 開頭要轉成純文字
- 新增功能：只新增一個檔案到 `categories/` 或 `handlers/`，不修改核心。
- 防護位置：防護 1、2 在 `core/claude.py`，防護 3、4 在 `core/pipeline.py`。每一段前面有「沒有防護時的預設行為」，整段註解掉仍可執行。
- 新增圖片類別必須同時新增 `tests/samples/<名稱>.json`，否則啟動失敗。詳見 `docs/adding-a-feature.md`。

## 常用指令

- 啟動：`uv run python main.py`
- 測試：`uv run pytest`（用假資料，不連 Discord、不呼叫 AI）

## 不可以 commit

- `.env`（含 `DISCORD_TOKEN`），只 commit `.env.example`
- `DATA_DIR` 裡的所有東西：圖片、資料庫、Excel
- `課程要求/` 資料夾
