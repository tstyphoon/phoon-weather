# phoon-weather

在自己電腦上執行的 Discord 天氣情報助理。頻道裡有人傳天氣相關圖片（天空、雷達或颱風圖、災情、預報截圖），它用 `claude -p` 判讀並建檔；用 `@bot` 問天氣，它查中央氣象署（台灣）與 Open-Meteo（海外、備援）後回答。

## 功能

- **圖片判讀**：不用 @bot，傳圖片就會處理。分類為天空、雷達或颱風圖、災情、預報截圖；無關圖片回一行說明並建檔。一則訊息最多處理 4 張。
- **文字查詢**：`@bot 台北明天會下雨嗎`。第一行直接回答，下面附氣溫、降雨機率、風速（m/s 與蒲福風級）、生效中的警特報。支援現在、今天、明天、後天。
- **分人設定**：`/setcity 城市` 設定自己的預設城市，每個人的設定與紀錄分開。
- **歷史與統計**：`/history [N]`、`/today`（含與上一筆的風速比較）、`/delete 編號`、`/help`。
- **排隊**：一次處理一件事，反應依序為 ⏳ → 🔄 → ✅ 或 ❌；前面排太多時會告知。
- **可擴充**：新增圖片類別或指令只需要新增一個檔案，見 [docs/adding-a-feature.md](docs/adding-a-feature.md)。

## 設定與啟動

1. 照 [docs/discord-server-setup.md](docs/discord-server-setup.md) 和 [docs/discord-bot-setup.md](docs/discord-bot-setup.md) 建立 Server 與 bot。
2. 複製 `.env.example` 成 `.env`，填入 `DISCORD_TOKEN`、`CHANNEL_ID`（以及選填的 `CWA_API_KEY`）。**`.env` 不會被 commit，金鑰不要貼給任何人。**
3. 啟動：

   ```
   uv run python main.py
   ```

   測試：`uv run pytest`（不連 Discord、不呼叫 AI）。

## 文件

- [requirements.md](requirements.md)：需求
- [docs/architecture.md](docs/architecture.md)：架構、四段防護、驗證清單
- [docs/adding-a-feature.md](docs/adding-a-feature.md)：怎麼新增功能

## 四段防護的位置

程式裡各用「防護 N 開始／結束」註解框起來（搜尋該字串即可），一開始全部開啟：

| 防護 | 檔案 |
|---|---|
| 1 `claude -p` 的檔案範圍隔離 | `core/claude.py` |
| 2 使用者文字只當資料 | `core/claude.py` |
| 3 模型回傳的名稱拿去當檔名前先清洗 | `core/pipeline.py` |
| 4 寫進紀錄與顯示的文字清洗 | `core/pipeline.py` |
