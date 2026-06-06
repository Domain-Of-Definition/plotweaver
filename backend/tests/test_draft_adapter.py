from app.chapter_parser import ParsedChapter
from app.draft_adapter import adapt_llm_chapter_draft
from app.models import LLMChapterDraft


def test_adapter_accepts_common_dialogue_variants() -> None:
    raw_data = {
        "summary": "林辰接到电话。",
        "scenes": [
            {
                "heading": "宿舍电话",
                "location": "教师宿舍",
                "time": "夜",
                "body": [
                    {
                        "type": "dialogue",
                        "speaker": "刑从连",
                        "content": "林先生是吗？",
                    }
                ],
            }
        ],
    }
    chapter = ParsedChapter(index=2, title="第二章", text="正文")

    adapted = adapt_llm_chapter_draft(raw_data, chapter)
    draft = LLMChapterDraft.model_validate(adapted)

    assert draft.chapter_index == 2
    assert draft.scenes[0].title == "宿舍电话"
    assert draft.scenes[0].body[0].type == "performance"
    assert draft.scenes[0].body[0].character_name == "刑从连"


def test_adapter_normalizes_role_type_variants() -> None:
    raw_data = {
        "scenes": [
            {
                "title": "电话",
                "setting": "宿舍",
                "body": [],
                "new_characters": [
                    {"name": "刑从连", "role_type": "配角"},
                    {"name": "林辰", "role_type": "PROTAGONIST"},
                ],
            }
        ],
    }
    chapter = ParsedChapter(index=1, title="第一章", text="正文")

    adapted = adapt_llm_chapter_draft(raw_data, chapter)
    draft = LLMChapterDraft.model_validate(adapted)

    assert draft.scenes[0].new_characters[0].role_type == "supporting"
    assert draft.scenes[0].new_characters[1].role_type == "protagonist"


def test_adapter_downgrades_unknown_passive_action_to_environment() -> None:
    raw_data = {
        "scenes": [
            {
                "title": "审讯室",
                "setting": "审讯室",
                "body": [
                    {
                        "type": "action",
                        "character_name": "未知角色",
                        "text": "片刻后，审讯室的门被再次打开。",
                    }
                ],
            }
        ],
    }
    chapter = ParsedChapter(index=1, title="第一章", text="正文")

    adapted = adapt_llm_chapter_draft(raw_data, chapter)
    draft = LLMChapterDraft.model_validate(adapted)

    assert draft.scenes[0].body[0].type == "environment"
    assert draft.scenes[0].body[0].text == "片刻后，审讯室的门被再次打开。"
