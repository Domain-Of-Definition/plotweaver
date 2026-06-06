from app.models import LLMChapterDraft
from app.normalizer import ScreenYAMLNormalizer


def test_normalizer_assigns_stable_character_id_and_strips_subject() -> None:
    chapter = LLMChapterDraft.model_validate(
        {
            "chapter_index": 1,
            "chapter_title": "第一章",
            "scenes": [
                {
                    "title": "水产店",
                    "camera_location": "外景",
                    "setting": "春水街水产店",
                    "time_of_day": "傍晚",
                    "characters_present": ["林辰"],
                    "new_characters": [
                        {
                            "name": "林辰",
                            "aliases": ["林老师"],
                            "description": "冷静敏锐。",
                            "role_type": "protagonist",
                        }
                    ],
                    "body": [
                        {
                            "type": "action",
                            "character_name": "林辰",
                            "text": "林辰俯身掀开塑料布，神色逐渐凝住。",
                        },
                        {
                            "type": "performance",
                            "character_name": "林老师",
                            "pre_action": "林老师避开飞溅的水滴。",
                            "dialogue": "这是什么？",
                            "post_action": "",
                        },
                    ],
                }
            ],
        }
    )

    normalizer = ScreenYAMLNormalizer()
    scenes = normalizer.normalize_chapter(chapter)

    assert normalizer.registry.characters[0].id == "char_001"
    assert scenes[0].characters_present == ["char_001"]
    assert scenes[0].body[0].text == "俯身掀开塑料布，神色逐渐凝住。"
    assert scenes[0].body[1].character_id == "char_001"
    assert scenes[0].body[1].pre_action == "避开飞溅的水滴。"
