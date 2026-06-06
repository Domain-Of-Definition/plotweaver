import json
from typing import Any, AsyncIterator


def sse_event(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


async def empty_conversion_stream() -> AsyncIterator[str]:
    yield sse_event("progress", {"message": "转换流已建立。"})
    yield sse_event(
        "error",
        {
            "message": "AI 转换管线尚未接入。当前阶段已完成 Schema、归一化与 API 骨架。",
            "code": "pipeline_not_implemented",
        },
    )
    yield sse_event("done", {"message": "转换流结束。"})
