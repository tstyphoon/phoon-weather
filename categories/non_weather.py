from core import Field, category


@category(
    name="non_weather", title="非天氣", icon="❔",
    description="與天氣無關的圖片",
    headline="這不是天氣相關，是 {what_is}",
    fields=[Field("what_is", str, label="這是什麼")],
    analyze=False,  # 分類那一步已經知道是什麼，不再多花一次呼叫
)
def non_weather(): ...
