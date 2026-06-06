from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chapter_parser import UploadParseError, parse_upload
from app.config import settings
from app.converter import stream_conversion
from app.validator import validate_screen_yaml_text


app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


class ValidateYAMLRequest(BaseModel):
    yaml_text: str


@app.post("/api/upload")
async def upload_novel(file: UploadFile = File(...)) -> dict:
    try:
        parsed = await parse_upload(file)
    except UploadParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": parsed.filename,
        "extension": parsed.extension,
        "word_count": parsed.word_count,
        "chapter_count": len(parsed.chapters),
        "chapters": [
            {"index": chapter.index, "title": chapter.title}
            for chapter in parsed.chapters
        ],
    }


@app.post("/api/validate-yaml")
def validate_yaml(request: ValidateYAMLRequest) -> dict:
    valid, errors = validate_screen_yaml_text(request.yaml_text)
    return {"valid": valid, "errors": errors}


@app.post("/api/convert/stream")
async def convert_stream(file: UploadFile = File(...)) -> StreamingResponse:
    try:
        parsed = await parse_upload(file)
    except UploadParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        stream_conversion(parsed),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
