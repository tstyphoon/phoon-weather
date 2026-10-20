from core import Field, category


@category(
    name="radar", title="雷達或颱風圖", icon="🌀",
    description="雷達回波圖、衛星雲圖、颱風路徑圖或其他氣象圖資截圖",
    headline="氣象圖資：{location}",
    fields=[
        Field("location", str, label="位置", desc="主要天氣系統或颱風的位置"),
        Field("intensity", str, label="強度", desc="例如強陣雨、中度颱風；看不出就寫「不明」"),
        Field("affected_area", str, label="影響區域"),
        Field("movement", str, label="移動方向", required=False),
    ],
)
def radar(): ...
