from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


NonEmptyStr = Annotated[str, Field(min_length=1)]
ReviewStatus = Literal["needs_review"]
RoleType = Literal["protagonist", "antagonist", "supporting", "minor", "unknown"]


class SourceChapter(BaseModel):
    index: int = Field(ge=1)
    title: NonEmptyStr


class Meta(BaseModel):
    title: NonEmptyStr
    author: str = ""
    version: str = "2.3.0"
    language: str = "zh-CN"
    source_chapters: list[SourceChapter] = Field(default_factory=list)


class Character(BaseModel):
    id: NonEmptyStr
    name: NonEmptyStr
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    role_type: RoleType = "unknown"


class ReviewMixin(BaseModel):
    status: ReviewStatus | None = None
    review_note: str | None = None

    @model_validator(mode="after")
    def review_note_requires_status(self):
        if self.review_note and self.status != "needs_review":
            self.status = "needs_review"
        return self


class EnvironmentBlock(ReviewMixin):
    type: Literal["environment"]
    text: NonEmptyStr


class ActionBlock(ReviewMixin):
    type: Literal["action"]
    character_id: NonEmptyStr
    character_name: NonEmptyStr
    text: NonEmptyStr


class PerformanceBlock(ReviewMixin):
    type: Literal["performance"]
    character_id: NonEmptyStr
    character_name: NonEmptyStr
    pre_action: str = ""
    dialogue: NonEmptyStr
    post_action: str = ""


class TransitionBlock(ReviewMixin):
    type: Literal["transition"]
    text: NonEmptyStr


BodyBlock = Annotated[
    EnvironmentBlock | ActionBlock | PerformanceBlock | TransitionBlock,
    Field(discriminator="type"),
]


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)
    source_chapter_index: int = Field(ge=1)
    source_hint: str = ""
    title: NonEmptyStr
    camera_location: str = "未知"
    setting: NonEmptyStr
    time_of_day: str = "未知"
    characters_present: list[str] = Field(default_factory=list)
    body: list[BodyBlock] = Field(default_factory=list)


class ScreenYAML(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    characters: list[Character] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)


class LLMCharacterDraft(BaseModel):
    name: NonEmptyStr
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    role_type: RoleType = "unknown"


class LLMEnvironmentDraft(BaseModel):
    type: Literal["environment"]
    text: NonEmptyStr


class LLMActionDraft(BaseModel):
    type: Literal["action"]
    character_name: NonEmptyStr
    text: NonEmptyStr


class LLMPerformanceDraft(BaseModel):
    type: Literal["performance"]
    character_name: NonEmptyStr
    pre_action: str = ""
    dialogue: NonEmptyStr
    post_action: str = ""


class LLMTransitionDraft(BaseModel):
    type: Literal["transition"]
    text: NonEmptyStr


LLMBodyDraft = Annotated[
    LLMEnvironmentDraft | LLMActionDraft | LLMPerformanceDraft | LLMTransitionDraft,
    Field(discriminator="type"),
]


class LLMSceneDraft(BaseModel):
    source_hint: str = ""
    title: NonEmptyStr
    camera_location: str = "未知"
    setting: NonEmptyStr
    time_of_day: str = "未知"
    characters_present: list[str] = Field(default_factory=list)
    new_characters: list[LLMCharacterDraft] = Field(default_factory=list)
    body: list[LLMBodyDraft] = Field(default_factory=list)


class LLMChapterDraft(BaseModel):
    chapter_index: int = Field(ge=1)
    chapter_title: NonEmptyStr
    summary: str = ""
    scenes: list[LLMSceneDraft] = Field(default_factory=list)
