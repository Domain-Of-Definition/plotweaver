from dataclasses import dataclass, field
import re

from app.models import (
    ActionBlock,
    BodyBlock,
    Character,
    EnvironmentBlock,
    LLMActionDraft,
    LLMChapterDraft,
    LLMEnvironmentDraft,
    LLMPerformanceDraft,
    LLMSceneDraft,
    LLMTransitionDraft,
    PerformanceBlock,
    Scene,
    TransitionBlock,
)


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _unique_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def strip_character_subject(text: str, character: Character) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""

    names = [character.name, *character.aliases]
    for name in sorted(_unique_values(names), key=len, reverse=True):
        escaped = re.escape(name)
        cleaned = re.sub(
            rf"^{escaped}(?:[：:，,。；;\s]|(?=[一-龥]))*",
            "",
            cleaned,
            count=1,
        ).strip()

    return cleaned


@dataclass
class CharacterRegistry:
    characters: list[Character] = field(default_factory=list)

    def _next_id(self) -> str:
        existing_numbers: list[int] = []
        for character in self.characters:
            match = re.fullmatch(r"char_(\d+)", character.id)
            if match:
                existing_numbers.append(int(match.group(1)))
        next_number = max(existing_numbers, default=0) + 1
        return f"char_{next_number:03d}"

    def _find_matches(self, name: str) -> list[Character]:
        cleaned = _clean_text(name)
        if not cleaned:
            return []

        matches: list[Character] = []
        for character in self.characters:
            names = [character.name, *character.aliases]
            if cleaned in _unique_values(names):
                matches.append(character)
        return matches

    def register_or_update(
        self,
        name: str,
        aliases: list[str] | None = None,
        description: str = "",
        role_type: str = "unknown",
    ) -> Character:
        cleaned_name = _clean_text(name)
        matches = self._find_matches(cleaned_name)

        if len(matches) == 1:
            character = matches[0]
            character.aliases = _unique_values(
                [*character.aliases, *(aliases or []), cleaned_name]
            )
            if description and not character.description:
                character.description = _clean_text(description)
            if character.role_type == "unknown" and role_type:
                character.role_type = role_type  # type: ignore[assignment]
            return character

        new_character = Character(
            id=self._next_id(),
            name=cleaned_name,
            aliases=_unique_values(aliases or []),
            description=_clean_text(description),
            role_type=role_type if role_type else "unknown",  # type: ignore[arg-type]
        )
        self.characters.append(new_character)
        return new_character

    def resolve(self, name: str) -> tuple[Character, str | None]:
        matches = self._find_matches(name)
        if len(matches) == 1:
            return matches[0], None

        if len(matches) > 1:
            character = matches[0]
            return character, f"角色名“{name}”匹配到多个已有角色，请人工核对。"

        character = self.register_or_update(name)
        return character, None


class ScreenYAMLNormalizer:
    def __init__(self, characters: list[Character] | None = None):
        self.registry = CharacterRegistry(characters or [])
        self.next_scene_index = 1

    def ingest_character_drafts(self, chapter: LLMChapterDraft) -> None:
        for scene in chapter.scenes:
            for draft in scene.new_characters:
                self.registry.register_or_update(
                    name=draft.name,
                    aliases=draft.aliases,
                    description=draft.description,
                    role_type=draft.role_type,
                )
            for name in scene.characters_present:
                self.registry.register_or_update(name=name)

    def normalize_chapter(self, chapter: LLMChapterDraft) -> list[Scene]:
        self.ingest_character_drafts(chapter)
        scenes: list[Scene] = []
        for scene_draft in chapter.scenes:
            scenes.append(
                self.normalize_scene(
                    scene_draft=scene_draft,
                    chapter_index=chapter.chapter_index,
                    scene_index=self.next_scene_index,
                )
            )
            self.next_scene_index += 1
        return scenes

    def normalize_scene(
        self,
        scene_draft: LLMSceneDraft,
        chapter_index: int,
        scene_index: int,
    ) -> Scene:
        body: list[BodyBlock] = []
        characters_present: set[str] = set()

        for block in scene_draft.body:
            normalized_block = self.normalize_block(block)
            body.append(normalized_block)

            character_id = getattr(normalized_block, "character_id", None)
            if character_id:
                characters_present.add(character_id)

        for name in scene_draft.characters_present:
            character, _ = self.registry.resolve(name)
            characters_present.add(character.id)

        return Scene(
            index=scene_index,
            source_chapter_index=chapter_index,
            source_hint=_clean_text(scene_draft.source_hint),
            title=_clean_text(scene_draft.title),
            camera_location=_clean_text(scene_draft.camera_location) or "未知",
            setting=_clean_text(scene_draft.setting),
            time_of_day=_clean_text(scene_draft.time_of_day) or "未知",
            characters_present=sorted(characters_present),
            body=body,
        )

    def normalize_block(
        self,
        block: LLMEnvironmentDraft
        | LLMActionDraft
        | LLMPerformanceDraft
        | LLMTransitionDraft,
    ) -> BodyBlock:
        if isinstance(block, LLMEnvironmentDraft):
            return EnvironmentBlock(type="environment", text=_clean_text(block.text))

        if isinstance(block, LLMTransitionDraft):
            return TransitionBlock(type="transition", text=_clean_text(block.text))

        if isinstance(block, LLMActionDraft):
            character, warning = self.registry.resolve(block.character_name)
            action = ActionBlock(
                type="action",
                character_id=character.id,
                character_name=character.name,
                text=strip_character_subject(block.text, character),
            )
            if warning:
                action.status = "needs_review"
                action.review_note = warning
            return action

        character, warning = self.registry.resolve(block.character_name)
        performance = PerformanceBlock(
            type="performance",
            character_id=character.id,
            character_name=character.name,
            pre_action=strip_character_subject(block.pre_action, character),
            dialogue=_clean_text(block.dialogue),
            post_action=strip_character_subject(block.post_action, character),
        )
        if warning:
            performance.status = "needs_review"
            performance.review_note = warning
        return performance
