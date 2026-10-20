from core import Field, category

from core import strings


@category(
    name="disaster", title="災情", icon="⚠️",
    description="淹水、強風、倒樹、土石流等天氣造成的災情照片",
    headline="災情：{disaster_type}（{severity}）",
    fields=[
        Field("disaster_type", str, label="災情類型", desc="例如淹水、倒樹、土石流"),
        Field("severity", str, label="嚴重程度", choices=["輕微", "中等", "嚴重"]),
        Field("advice", str, label="建議行動", desc="給一般民眾的簡短建議"),
        Field("location", str, label="地點", required=False, desc="看得出縣市才填"),
    ],
    footer_notes=[strings.DISASTER_NOTE],
)
def disaster(): ...
