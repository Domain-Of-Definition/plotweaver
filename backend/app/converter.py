from collections.abc import AsyncIterator

from pydantic import ValidationError

from app.chapter_parser import ParsedNovel
from app.draft_adapter import adapt_llm_chapter_draft
from app.llm_client import LLMClient, LLMError
from app.models import LLMChapterDraft, Meta, ScreenYAML, SourceChapter
from app.normalizer import ScreenYAMLNormalizer
from app.prompt_templates import SYSTEM_PROMPT, build_chapter_prompt
from app.sse import sse_event
from app.validator import validate_screen_yaml_data
from app.yaml_service import (
    dump_scene_yaml,
    dump_screen_yaml,
    render_c_fountain,
    render_scene_c_fountain,
)


async def stream_conversion(parsed: ParsedNovel) -> AsyncIterator[str]:
    normalizer = ScreenYAMLNormalizer()
    all_scenes = []
    previous_summary = ""

    try:
        client = LLMClient()
        total_chapters = len(parsed.chapters)

        yield sse_event(
            "progress",
            {
                "message": "开始转换。",
                "total_chapters": total_chapters,
                "completed_chapters": 0,
            },
        )

        for chapter in parsed.chapters:
            yield sse_event(
                "chapter_started",
                {
                    "chapter_index": chapter.index,
                    "chapter_title": chapter.title,
                    "total_chapters": total_chapters,
                },
            )

            prompt = build_chapter_prompt(
                chapter=chapter,
                existing_characters=normalizer.registry.characters,
                previous_summary=previous_summary,
            )
            raw_data = await client.complete_json(SYSTEM_PROMPT, prompt)
            adapted_data = adapt_llm_chapter_draft(raw_data, chapter)
            chapter_draft = LLMChapterDraft.model_validate(adapted_data)
            previous_summary = chapter_draft.summary[:500]

            scenes = normalizer.normalize_chapter(chapter_draft)
            for scene in scenes:
                all_scenes.append(scene)
                yield sse_event(
                    "scene_completed",
                    {
                        "chapter_index": chapter.index,
                        "scene": scene.model_dump(exclude_none=True),
                        "scene_yaml": dump_scene_yaml(scene),
                        "fountain": render_scene_c_fountain(scene),
                    },
                )

            yield sse_event(
                "progress",
                {
                    "message": f"已完成第 {chapter.index} 章。",
                    "total_chapters": total_chapters,
                    "completed_chapters": chapter.index,
                    "scene_count": len(all_scenes),
                },
            )

        script = ScreenYAML(
            meta=Meta(
                title=guess_title(parsed.filename),
                source_chapters=[
                    SourceChapter(index=chapter.index, title=chapter.title)
                    for chapter in parsed.chapters
                ],
            ),
            characters=normalizer.registry.characters,
            scenes=all_scenes,
        )

        valid, errors = validate_screen_yaml_data(script.model_dump())
        yield sse_event("validation_result", {"valid": valid, "errors": errors})

        yaml_text = dump_screen_yaml(script)
        fountain_text = render_c_fountain(script)
        yield sse_event(
            "final_yaml",
            {
                "yaml": yaml_text,
                "fountain": fountain_text,
                "characters": [character.model_dump() for character in script.characters],
                "scene_count": len(script.scenes),
            },
        )
        yield sse_event("done", {"message": "转换完成。"})

    except LLMError as exc:
        yield sse_event("error", {"message": str(exc), "code": "llm_error"})
        yield sse_event("done", {"message": "转换流结束。"})
    except ValidationError as exc:
        yield sse_event(
            "error",
            {
                "message": "模型返回结构不符合 LLMChapterDraft。",
                "code": "draft_validation_error",
                "errors": [
                    {
                        "location": ".".join(str(part) for part in error.get("loc", [])),
                        "message": error.get("msg", "validation error"),
                    }
                    for error in exc.errors()
                ],
            },
        )
        yield sse_event("done", {"message": "转换流结束。"})
    except Exception as exc:
        yield sse_event("error", {"message": str(exc), "code": "conversion_error"})
        yield sse_event("done", {"message": "转换流结束。"})


def guess_title(filename: str) -> str:
    for suffix in [".txt", ".docx"]:
        if filename.lower().endswith(suffix):
            return filename[: -len(suffix)]
    return filename or "未命名剧本"
