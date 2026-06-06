from dataclasses import dataclass
import re

import ebooklib
from docx import Document
from ebooklib import epub
from fastapi import UploadFile
from bs4 import BeautifulSoup


MIN_CHAPTERS = 3
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".txt", ".docx", ".epub"}


@dataclass(frozen=True)
class ParsedChapter:
    index: int
    title: str
    text: str


@dataclass(frozen=True)
class ParsedNovel:
    filename: str
    extension: str
    text: str
    chapters: list[ParsedChapter]

    @property
    def word_count(self) -> int:
        compact = re.sub(r"\s+", "", self.text)
        return len(compact)


class UploadParseError(ValueError):
    pass


CHAPTER_TITLE_RE = re.compile(
    r"^\s*(第\s*[零〇一二两三四五六七八九十百千万\d]+\s*[章节回卷集部篇]"
    r"(?:[：:\-\s].*)?|Chapter\s+(?:\d+|[A-Za-z]+)(?:[：:\-\s].*)?)\s*$",
    re.IGNORECASE,
)


def get_extension(filename: str) -> str:
    lowered = filename.lower()
    for extension in [".docx", ".epub", ".txt", ".pdf"]:
        if lowered.endswith(extension):
            return extension
    return ""


async def parse_upload(file: UploadFile) -> ParsedNovel:
    filename = file.filename or "novel"
    extension = get_extension(filename)

    if extension == ".pdf":
        raise UploadParseError("v1 暂不支持 PDF，请转换为 TXT 或 DOCX 后再上传。")
    if extension not in SUPPORTED_EXTENSIONS:
        raise UploadParseError("仅支持 TXT 或 DOCX 文件。")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadParseError("文件过大，请上传 8MB 以内的小说文本。")

    if extension == ".txt":
        text = decode_text(content)
        chapters = split_chapters(text)
    elif extension == ".docx":
        text = extract_docx_text(content)
        chapters = split_chapters(text)
    else:
        chapters = extract_epub_chapters(content)
        text = "\n\n".join(f"{chapter.title}\n{chapter.text}" for chapter in chapters)

    if len(chapters) < MIN_CHAPTERS:
        raise UploadParseError("系统要求至少 3 个章节，请上传包含 3 章以上的小说。")

    return ParsedNovel(filename=filename, extension=extension, text=text, chapters=chapters)


def decode_text(content: bytes) -> str:
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk", "big5"]
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UploadParseError("无法识别文本编码，请转换为 UTF-8 后重试。")


def extract_docx_text(content: bytes) -> str:
    from io import BytesIO

    document = Document(BytesIO(content))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
    return "\n".join(paragraph for paragraph in paragraphs if paragraph)


def extract_epub_chapters(content: bytes) -> list[ParsedChapter]:
    import tempfile
    from pathlib import Path

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        book = epub.read_epub(str(temp_path))
    except Exception as exc:
        raise UploadParseError("EPUB 文件解析失败，请确认文件未加密且格式完整。") from exc
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)

    chapters: list[ParsedChapter] = []
    order = 1
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        item_name = item.get_name().lower()
        if any(marker in item_name for marker in ["nav", "toc", "cover"]):
            continue

        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = extract_soup_text(soup)
        if not text:
            continue

        title = extract_soup_title(soup) or f"EPUB 章节 {order}"
        chapters.append(ParsedChapter(index=order, title=title, text=text))
        order += 1

    return chapters


def extract_soup_title(soup: BeautifulSoup) -> str:
    for selector in ["h1", "h2", "h3", "title"]:
        node = soup.find(selector)
        if node:
            title = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
            if title:
                return title
    return ""


def extract_soup_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "aside"]):
        tag.decompose()

    paragraphs: list[str] = []
    primary_nodes = soup.find_all(["h1", "h2", "h3", "p"])
    nodes = primary_nodes if primary_nodes else soup.find_all(["div"])
    for node in nodes:
        text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
        if text and text not in paragraphs:
            paragraphs.append(text)

    return "\n".join(paragraphs).strip()


def split_chapters(text: str) -> list[ParsedChapter]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    headings: list[tuple[int, str]] = []

    for line_index, line in enumerate(lines):
        title = line.strip()
        if title and CHAPTER_TITLE_RE.match(title):
            headings.append((line_index, title))

    if not headings:
        return [ParsedChapter(index=1, title="全文", text=normalized.strip())]

    chapters: list[ParsedChapter] = []
    for order, (start_line, title) in enumerate(headings, start=1):
        next_start = headings[order][0] if order < len(headings) else len(lines)
        chapter_text = "\n".join(lines[start_line + 1 : next_start]).strip()
        chapters.append(ParsedChapter(index=order, title=title, text=chapter_text))

    return [chapter for chapter in chapters if chapter.text]
