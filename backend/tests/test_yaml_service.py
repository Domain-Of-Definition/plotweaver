from app.models import ActionBlock, Scene
from app.yaml_service import render_scene_c_fountain


def test_render_scene_c_fountain() -> None:
    scene = Scene(
        index=1,
        source_chapter_index=1,
        title="水产店",
        camera_location="外景",
        setting="春水街水产店",
        time_of_day="傍晚",
        characters_present=["char_001"],
        body=[
            ActionBlock(
                type="action",
                character_id="char_001",
                character_name="林辰",
                text="俯身掀开塑料布。",
            )
        ],
    )

    text = render_scene_c_fountain(scene)

    assert "第 1 场 （第 1 章）" in text
    assert "外景 / 春水街水产店 / 傍晚" in text
    assert "林辰：（俯身掀开塑料布。）" in text
