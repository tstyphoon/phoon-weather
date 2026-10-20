# Discord Bot 設定步驟

目標：建立你自己的 bot（機器人帳號），拿到 bot token，並把它邀進你的 Server。

先完成 [discord-server-setup.md](discord-server-setup.md)，你需要已經有 Server 和 `# 天氣助理` 頻道。

名詞：
- **Application（應用程式）**：你在 Discord 註冊的一個專案，bot 是裡面的一部分。
- **Bot**：看起來像一個普通帳號，但由你的程式操作。我們的 agent 就是用這個帳號進出頻道。
- **Bot token（機器人金鑰）**：bot 的密碼。程式拿著它才能登入成為這個 bot。
- **Intent（權限開關）**：Discord 預設不給 bot 看某些資料，需要你在後台明確打開。

---

## ⚠️ 先看這一段：bot token 的規矩

**bot token 絕對不能：**
- **貼給任何人**（同學、老師、朋友都不行）
- **貼進和 Claude 的對話**（包括這個對話）
- **commit 進 git**，也不能放在任何會上傳到 GitHub 的檔案裡
- 放在截圖、螢幕錄影、文件、聊天室裡

拿到 token 的人，就能完全冒用你的 bot。它只能放在你電腦上的 `.env` 檔（`.env` 已經列在 `.gitignore`，不會被 commit）。

**萬一不小心洩漏了：** 立刻回到 Developer Portal 的 Bot 頁面按 **Reset Token**（見下面 C 的第 4 步），舊的 token 馬上失效。如果已經 commit 進 git，重新產生 token 之後，還要另外開新的 repo 重新 commit（舊的 commit 紀錄裡仍然看得到）。

---

## A. 建立 Application 與 Bot

1. 打開瀏覽器，到 **https://discord.com/developers/applications**，用你的 Discord 帳號登入。
2. 點畫面**右上角的藍紫色按鈕 「New Application」**（新增應用程式）。
3. 「Name」欄位輸入名字，例如 `phoon-weather`。這也是 bot 在頻道裡顯示的名字。
4. 勾選同意服務條款，按 **「Create」**。
5. 你會進到這個應用程式的設定頁。左邊有一排選單，之後會用到：**General Information、Installation、OAuth2、Bot**。

---

## B. 打開 Message Content Intent（一定要）

**為什麼一定要：** 預設情況下，Discord 不會把「訊息內容」交給 bot。我們的 agent 需要讀：
- 使用者 `@bot` 問天氣時**打的字**（例如「台北明天會下雨嗎」）
- 使用者傳圖片時**附帶的說明文字**
- 判斷訊息是不是 `/` 指令之外的一般聊天

沒打開的話，bot 看得到有訊息，卻看不到內容，文字查詢就不會運作，程式啟動時也可能直接報錯。

步驟：
1. 在左邊選單點 **「Bot」**。
2. 往下捲到 **「Privileged Gateway Intents」** 區塊。
3. 把 **「MESSAGE CONTENT INTENT」** 的開關**打開**（變成藍色）。
4. 另外兩個（Presence Intent、Server Members Intent）**保持關閉**，我們用不到。
5. 頁面最下面會跳出一條提示「Careful — you have unsaved changes」，按 **「Save Changes」**。

---

## C. 拿到 Bot Token

1. 還在左邊的 **「Bot」** 頁面。
2. 找到 **「Token」** 區塊，點 **「Reset Token」**（第一次可能顯示「Reset Token」或「Copy」）。
3. 跳出確認視窗，按 **「Yes, do it!」**。如果要求輸入密碼或兩步驟驗證碼，照著做。
4. token 會**只出現這一次**，一長串英數字加點。馬上點 **「Copy」** 複製。
5. 直接貼到 `.env` 檔裡（見最後一節），**不要貼到別的地方**。
6. 如果沒來得及複製，或不確定有沒有外流，再按一次 **Reset Token** 重新產生一個，舊的就作廢。

### 順便建議：關掉 Public Bot
在同一個 Bot 頁面，找到 **「Public Bot」** 開關，**關閉**它。這樣別人就不能自己把你的 bot 邀進他的 Server。

---

## D. 決定 bot 需要的權限

我們的 agent 需要在 `# 天氣助理` 頻道裡做這些事，對應的權限：

| agent 要做的事 | Discord 權限名稱（英文） |
|---|---|
| 看得到頻道 | View Channels |
| 回覆訊息、發送開機通知 | Send Messages |
| 用「回覆」那則圖片訊息的方式送出 | Read Message History |
| 傳出卡片（有框有欄位的訊息） | Embed Links |
| 在訊息上加 ⏳🔄✅❌ | Add Reactions |
| 使用 `/setcity` 這類指令 | Use Application Commands（由下面的 scope 取得） |

**不要勾的權限：** Administrator、Manage Server、Manage Messages、Mention Everyone 等。權限給越少越安全，萬一 bot 出狀況，能造成的影響也越小。

---

## E. 產生邀請連結，把 Bot 邀進你的 Server

1. 在左邊選單點 **「OAuth2」**。
2. 往下找到 **「OAuth2 URL Generator」** 區塊。
3. 在 **「Scopes」**（範圍）勾選：
   - **`bot`**
   - **`applications.commands`**（讓 `/setcity` 這類指令可以用）
4. 勾了 `bot` 之後，下方會出現 **「Bot Permissions」** 區塊，勾選：
   - **View Channels**
   - **Send Messages**
   - **Read Message History**
   - **Embed Links**
   - **Add Reactions**
5. 頁面最下面有 **「Generated URL」**，是一長串網址。按旁邊的 **「Copy」**。
6. 把這個網址貼到瀏覽器網址列，按 Enter。
7. 頁面問「Add to server」，在下拉選單選**你自己的那個 Server**（要有「管理伺服器」權限才看得到，你自己建的 Server 一定有）。
8. 按 **「繼續」**（Continue），確認權限清單跟上面一致，再按 **「授權」**（Authorize）。
9. 可能出現「我不是機器人」驗證，照做。
10. 回到 Discord，你會在頻道看到一則「歡迎 phoon-weather」之類的系統訊息；右邊成員列表會出現 bot（顯示離線，因為程式還沒跑）。

> 這個邀請網址不包含 token，可以保存，之後要再邀請就再用一次。

### 讓 bot 能看到 `# 天氣助理` 頻道
如果你有把頻道設為私人，要在頻道設定的「權限」裡，加入 bot 的角色並允許上面的權限。第一版的做法：頻道保持公開，就不用額外設定。

---

## F. 把 token 與 CHANNEL_ID 放進 .env（只在你的電腦上）

1. 用檔案總管打開專案資料夾 `C:\Users\user\phoon-weather`。
2. 打開 **記事本**，輸入下面內容（把後面換成你自己的值，**不要有空格、不要加引號**）：

   ```
   DISCORD_TOKEN=你剛複製的token
   CHANNEL_ID=你之前記下的頻道ID
   CLAUDE_MODEL=haiku
   DATA_DIR=data
   DEFAULT_CITY=台北
   CWA_API_KEY=你在中央氣象署申請的授權碼
   ```

   `CWA_API_KEY` 跟 `DISCORD_TOKEN` 一樣是金鑰，不能貼給別人、不能貼進對話、不能 commit。

3. 按 **檔案 → 另存新檔**。
4. 存檔位置選專案資料夾。「存檔類型」選 **「所有檔案」**，「檔案名稱」輸入 **`.env`**（開頭有一個點，結尾沒有 `.txt`）。
5. 按存檔。檔案總管裡如果看到 `.env.txt`，代表存錯了，需要改名成 `.env`（可能要在檔案總管的「檢視」打開「副檔名」才看得到）。
6. **確認這個檔案不會被 commit：** 專案裡的 `.gitignore` 已經列了 `.env`。不要把它複製到別的資料夾、不要截圖、不要貼到對話。

---

## 完成確認

- [ ] Developer Portal 裡有你的 application
- [ ] Bot 頁面的 **Message Content Intent** 是打開（藍色）並且已儲存
- [ ] Public Bot 已關閉
- [ ] 你的 Server 成員列表裡看得到 bot（離線）
- [ ] 專案資料夾有 `.env`，裡面有 `DISCORD_TOKEN` 和 `CHANNEL_ID`
- [ ] 你沒有把 token 貼給任何人、也沒有貼進任何對話

之後 agent 開始跑時，bot 會變成「線上」。
