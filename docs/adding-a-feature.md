# 怎麼新增功能

原則：**只新增一個檔案，不修改核心**。重開 agent 就生效。防護和驗證都在核心，新功能繞不過去，也不用自己做。

## 一、新增一種圖片判讀類別

例：新增「冰雹照片」。

1. 新增檔案 `categories/hail.py`：

   ```python
   from core import Field, category

   @category(
       name="hail",                    # 程式用的代號，英文小寫
       title="冰雹", icon="🧊",
       description="冰雹或冰雹造成損害的照片",    # 給分類器判斷用，寫清楚「什麼樣的圖算這類」
       headline="冰雹：直徑約 {size_cm} 公分",     # 卡片最上方的一句話，{} 內是下面的欄位名
       fields=[
           Field("size_cm", float, label="直徑（公分）", min=0, max=30),
           Field("severity", str, label="嚴重程度", choices=["輕微", "中等", "嚴重"]),
       ],
   )
   def hail(): ...
   ```

   - 需要額外運算（例如換算）時，才在函式裡寫：接收驗證過的資料 dict，回傳要追加的欄位 dict，並在 `@category` 加上 `extra_labels={"欄位名": "顯示名稱"}`。可參考 `categories/forecast_shot.py`。
   - 欄位選填就加 `required=False`；數字欄位寫 `min`、`max`；有固定選項就寫 `choices`。
   - 類別專屬的頁尾提醒用 `footer_notes=[...]`（例如災情類的 119 提醒）。

2. 新增測試樣本 `tests/samples/hail.json`（**沒有樣本，程式會啟動失敗**）：

   ```json
   {"model_output": {"size_cm": 2.5, "severity": "中等", "confidence": "高"},
    "expect_headline": "冰雹：直徑約 2.5 公分"}
   ```

3. 執行 `uv run pytest`。既有的測試會自動涵蓋新類別。

核心會自動幫你：加進分類選項、產生判讀提示詞與輸出格式、驗證模型回傳、清洗文字與檔名、建檔存圖、組卡片與頁尾、納入 `/history`、`/today`、`/help`。

## 二、新增一個 / 指令

例：`/wind 風速` 換算蒲福風級。新增 `handlers/wind.py`：

```python
from core import command
from services.units import beaufort

@command("wind", description="把風速（m/s）換算成蒲福風級", usage="/wind 風速（例如 /wind 8.5）")
async def wind(ctx, speed: float):
    return f"{speed:g} m/s 是蒲福 {beaufort(speed)} 級"
```

- 指令的參數寫在第二個位置，型別寫 `str`、`int` 或 `float`，核心會自動轉換；轉不過就回覆用法。
- `ctx` 提供：`ctx.user_id`、`ctx.user_name`、`ctx.store`（資料庫）、`ctx.weather`（天氣）、`ctx.city`（這個人設定的城市）。
- 回傳的字串就是回覆內容。
- 名稱重複時，程式啟動會失敗並告訴你。

## 三、新增一個 @bot 文字功能

新增 `handlers/xxx.py`，用 `@text_intent("名稱", keywords=("關鍵字",))`。問句只要含有任一關鍵字就會交給它；沒有關鍵字的那一個（目前是 `weather_query`）是預設處理者，只能有一個。

## 四、需要新的外部資料來源

在 `services/` 加一個薄包裝（只管呼叫與整理），讓 handler 去用，不要在 handler 裡直接寫網路請求細節。**金鑰一律放 `.env`**，並在 `core/config.py` 加上讀取。

## 檢查清單

- [ ] 只新增了檔案，沒有改 `core/`
- [ ] 圖片類別有附 `tests/samples/<名稱>.json`
- [ ] `uv run pytest` 全部通過
- [ ] 重開 agent，輸入 `/help` 看得到新功能
