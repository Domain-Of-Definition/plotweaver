from typing import Any

import yaml

from app.models import (
    ActionBlock,
    EnvironmentBlock,
    PerformanceBlock,
    Scene,
    ScreenYAML,
    TransitionBlock,
)


def dump_screen_yaml(script: ScreenYAML) -> str:
    data = script.model_dump(exclude_none=True)
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def load_screen_yaml(raw_yaml: str) -> ScreenYAML:
    data: Any = yaml.safe_load(raw_yaml)
    return ScreenYAML.model_validate(data)


def _wrap_action(text: str | None) -> str:
    cleaned = (text or "").strip()
    return f"（{cleaned}）" if cleaned else ""


def render_scene_heading(scene: Scene) -> str:
    camera_location = scene.camera_location.strip() or "未知"
    if camera_location == "未知":
        camera_location = "场景"
    return (
        f"第 {scene.index} 场 （第 {scene.source_chapter_index} 章）\n"
        f"{camera_location} / {scene.setting} / {scene.time_of_day}"
    )


def render_c_fountain(script: ScreenYAML, include_ai_flags: bool = False) -> str:
    parts: list[str] = []

    if script.meta.title:
        parts.append(f"Title: {script.meta.title}")
    if script.meta.author:
        parts.append(f"Author: {script.meta.author}")

    for scene in script.scenes:
        parts.append("")
        parts.append("")
        parts.append(render_scene_heading(scene))
        parts.append("")

        for block in scene.body:
            if include_ai_flags and block.status == "needs_review" and block.review_note:
                parts.append(f"# AI提示：{block.review_note}")

            if isinstance(block, EnvironmentBlock):
                parts.append(_wrap_action(block.text))
            elif isinstance(block, ActionBlock):
                parts.append(f"{block.character_name}：{_wrap_action(block.text)}")
            elif isinstance(block, PerformanceBlock):
                pre = _wrap_action(block.pre_action)
                post = _wrap_action(block.post_action)
                parts.append(f"{block.character_name}：{pre}{block.dialogue}{post}")
            elif isinstance(block, TransitionBlock):
                parts.append(f"> {block.text}")

            parts.append("")

    return "\n".join(parts).strip() + "\n"


def dump_scene_yaml(scene: Scene) -> str:
    data = scene.model_dump(exclude_none=True)
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def render_scene_c_fountain(scene: Scene, include_ai_flags: bool = False) -> str:
    parts: list[str] = []
    parts.append(render_scene_heading(scene))
    parts.append("")

    for block in scene.body:
        if include_ai_flags and block.status == "needs_review" and block.review_note:
            parts.append(f"# AI提示：{block.review_note}")

        if isinstance(block, EnvironmentBlock):
            parts.append(_wrap_action(block.text))
        elif isinstance(block, ActionBlock):
            parts.append(f"{block.character_name}：{_wrap_action(block.text)}")
        elif isinstance(block, PerformanceBlock):
            pre = _wrap_action(block.pre_action)
            post = _wrap_action(block.post_action)
            parts.append(f"{block.character_name}：{pre}{block.dialogue}{post}")
        elif isinstance(block, TransitionBlock):
            parts.append(f"> {block.text}")

        parts.append("")

    return "\n".join(parts).strip() + "\n"


def render_chinese_preview(script: ScreenYAML) -> str:
    parts: list[str] = []

    for scene in script.scenes:
        parts.append("")
        parts.append(render_scene_heading(scene))
        parts.append("")

        for block in scene.body:
            if isinstance(block, EnvironmentBlock):
                parts.append(_wrap_action(block.text))
            elif isinstance(block, ActionBlock):
                parts.append(f"{block.character_name}：{_wrap_action(block.text)}")
            elif isinstance(block, PerformanceBlock):
                pre = _wrap_action(block.pre_action)
                post = _wrap_action(block.post_action)
                parts.append(f"{block.character_name}：{pre}{block.dialogue}{post}")
            elif isinstance(block, TransitionBlock):
                parts.append(block.text)

            parts.append("")

    return "\n".join(parts).strip() + "\n"
