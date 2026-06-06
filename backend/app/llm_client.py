import json
import re
from typing import Any

from openai import AsyncOpenAI

from app.config import settings


class LLMError(RuntimeError):
    pass


def extract_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if not cleaned:
        raise LLMError("模型返回内容为空，无法解析为 JSON。")

    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMError("模型返回内容不是有效 JSON。")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"模型返回 JSON 解析失败: {exc}") from exc

    if not isinstance(data, dict):
        raise LLMError("模型返回 JSON 顶层必须是对象。")
    return data


class LLMClient:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise LLMError("未配置 OPENAI_API_KEY。")

        kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        self.client = AsyncOpenAI(**kwargs)

    async def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response_format = None
        if settings.openai_response_format == "json_object":
            response_format = {"type": "json_object"}

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                temperature=settings.openai_temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_format,
            )
        except Exception as exc:
            raise LLMError(f"模型接口请求失败: {exc}") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMError("模型返回内容为空，无法解析为 JSON。")
        return extract_json_object(content)
