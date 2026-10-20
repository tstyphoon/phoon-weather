from core import Field, category


@category(
    name="sky", title="天空", icon="🌤️",
    description="天空、雲、閃電、彩虹等實景照片",
    headline="天空：{weather}",
    fields=[
        Field("weather", str, label="天氣現象", desc="例如晴朗、多雲、積雨雲、閃電"),
        Field("cloud_type", str, label="雲型", desc="看不出雲型就寫「無明顯雲型」"),
        Field("outlook", str, label="未來 1 到 3 小時", desc="依畫面推測的短時間變化，一句話，30 字內"),
    ],
)
def sky(): ...
