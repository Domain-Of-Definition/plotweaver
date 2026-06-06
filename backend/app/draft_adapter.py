from copy import deepcopy
from typing import Any

from app.chapter_parser import ParsedChapter


BODY_TYPE_ALIASES = {
    "env": "environment",
    "environment": "environment",
    "scene": "environment",
    "setting": "environment",
    "description": "environment",
    "action": "action",
    "behavior": "action",
    "movement": "action",
    "dialogue": "performance",
    "dialog": "performance",
    "line": "performance",
    "performance": "performance",
    "transition": "transition",
}


def adapt_llm_chapter_draft(raw_data: dict[str, Any], chapter: ParsedChapter) -> dict[str, Any]:
    data = deepcopy(raw_data)

    if "scenes" not in data and isinstance(data.get("script"), list):
        data["scenes"] = data["script"]
    if "scenes" not in data and isinstance(data.get("scene"), dict):
        data["scenes"] = [data["scene"]]

    data.setdefault("chapter_index", chapter.index)
    data.setdefault("chapter_title", chapter.title)
    data.setdefault("summary", "")
    data["scenes"] = [adapt_scene(scene) for scene in data.get("scenes", []) if isinstance(scene, dict)]
    return data


def adapt_scene(scene: dict[str, Any]) -> dict[str, Any]:
    adapted = deepcopy(scene)
    adapted.setdefault("source_hint", adapted.get("source") or adapted.get("source_excerpt") or "")
    adapted.setdefault("title", adapted.get("name") or adapted.get("heading") or "未命名场景")
    adapted.setdefault("camera_location", adapted.get("camera") or adapted.get("location_type") or "未知")
    adapted.setdefault("setting", adapted.get("location") or adapted.get("place") or adapted.get("title") or "未知地点")
    adapted.setdefault("time_of_day", adapted.get("time") or adapted.get("timeOfDay") or "未知")

    if "characters_present" not in adapted:
        adapted["characters_present"] = adapted.get("characters") or adapted.get("present_characters") or []
    adapted["characters_present"] = normalize_name_list(adapted.get("characters_present"))

    if "new_characters" not in adapted:
        adapted["new_characters"] = adapted.get("character_drafts") or adapted.get("newCharacters") or []
    adapted["new_characters"] = [
        adapt_character(character)
        for character in adapted.get("new_characters", [])
        if isinstance(character, dict)
    ]

    adapted["body"] = [adapt_body_block(block) for block in adapted.get("body", []) if isinstance(block, dict)]
    return adapted


def adapt_character(character: dict[str, Any]) -> dict[str, Any]:
    adapted = deepcopy(character)
    adapted.setdefault("name", adapted.get("character_name") or adapted.get("display_name") or "未知角色")
    adapted.setdefault("aliases", adapted.get("alias") or [])
    adapted["aliases"] = normalize_name_list(adapted.get("aliases"))
    adapted.setdefault("description", adapted.get("desc") or "")
    adapted["role_type"] = normalize_role_type(adapted.get("role_type") or adapted.get("role"))
    return adapted


def adapt_body_block(block: dict[str, Any]) -> dict[str, Any]:
    adapted = deepcopy(block)
    block_type = str(adapted.get("type") or "").strip().lower()
    adapted["type"] = BODY_TYPE_ALIASES.get(block_type, block_type or "environment")

    if adapted["type"] == "environment":
        adapted.setdefault("text", adapted.get("content") or adapted.get("description") or "")
        return pick_keys(adapted, ["type", "text"])

    if adapted["type"] == "transition":
        adapted.setdefault("text", adapted.get("content") or adapted.get("description") or "切至：")
        return pick_keys(adapted, ["type", "text"])

    character_name = (
        adapted.get("character_name")
        or adapted.get("speaker")
        or adapted.get("character")
        or adapted.get("name")
        or "未知角色"
    )

    if adapted["type"] == "action":
        adapted.setdefault("text", adapted.get("content") or adapted.get("description") or "")
        adapted["character_name"] = character_name
        if should_downgrade_unknown_action_to_environment(character_name, adapted.get("text")):
            return {"type": "environment", "text": str(adapted.get("text") or "").strip()}
        return pick_keys(adapted, ["type", "character_name", "text"])

    adapted["type"] = "performance"
    adapted["character_name"] = character_name
    adapted.setdefault("pre_action", adapted.get("before") or adapted.get("before_action") or "")
    adapted.setdefault("dialogue", adapted.get("content") or adapted.get("text") or adapted.get("line") or "")
    adapted.setdefault("post_action", adapted.get("after") or adapted.get("after_action") or "")
    return pick_keys(adapted, ["type", "character_name", "pre_action", "dialogue", "post_action"])


def normalize_name_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def should_downgrade_unknown_action_to_environment(character_name: Any, text: Any) -> bool:
    name = str(character_name or "").strip()
    content = str(text or "").strip()
    if name not in {"未知角色", "未知", "某人", "有人", "某个角色"}:
        return False
    passive_markers = [
        "被打开",
        "被再次打开",
        "被推开",
        "被再次推开",
        "被拉开",
        "被带进",
        "被带入",
        "被放在",
        "被递出",
    ]
    return any(marker in content for marker in passive_markers)


def normalize_role_type(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    role_aliases = {
        "主角": "protagonist",
        "主人公": "protagonist",
        "男主": "protagonist",
        "女主": "protagonist",
        "protagonist": "protagonist",
        "反派": "antagonist",
        "敌人": "antagonist",
        "antagonist": "antagonist",
        "配角": "supporting",
        "重要配角": "supporting",
        "supporting": "supporting",
        "supporting character": "supporting",
        "次要角色": "minor",
        "小角色": "minor",
        "路人": "minor",
        "minor": "minor",
        "未知": "unknown",
        "不明": "unknown",
        "unknown": "unknown",
    }
    if normalized in role_aliases:
        return role_aliases[normalized]
    allowed = {"protagonist", "antagonist", "supporting", "minor", "unknown"}
    return normalized if normalized in allowed else "unknown"


def pick_keys(data: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: data.get(key) for key in keys}
