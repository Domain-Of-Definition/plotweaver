from pydantic import ValidationError

from app.models import ScreenYAML
from app.yaml_service import load_screen_yaml


def validate_screen_yaml_data(data: object) -> tuple[bool, list[str]]:
    try:
        ScreenYAML.model_validate(data)
        return True, []
    except ValidationError as exc:
        return False, [format_validation_error(error) for error in exc.errors()]


def validate_screen_yaml_text(raw_yaml: str) -> tuple[bool, list[str]]:
    try:
        load_screen_yaml(raw_yaml)
        return True, []
    except ValidationError as exc:
        return False, [format_validation_error(error) for error in exc.errors()]
    except Exception as exc:
        return False, [str(exc)]


def format_validation_error(error: dict) -> str:
    location = ".".join(str(part) for part in error.get("loc", []))
    message = error.get("msg", "validation error")
    return f"{location}: {message}" if location else message
