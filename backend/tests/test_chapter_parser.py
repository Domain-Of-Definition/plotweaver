from app.chapter_parser import split_chapters
from app.chapter_parser import extract_epub_chapters


def build_epub_bytes() -> bytes:
    from io import BytesIO

    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("plotweaver-test")
    book.set_title("测试小说")
    book.set_language("zh-CN")

    items = []
    for index in range(1, 4):
        chapter = epub.EpubHtml(
            title=f"第{index}章",
            file_name=f"chapter_{index}.xhtml",
            lang="zh-CN",
        )
        chapter.content = (
            f"<html><body><h1>第{index}章</h1>"
            f"<p>这是第{index}章的正文，人物走进房间，灯光落在桌面上。</p>"
            f"<p>这一段用于保证章节长度足够，不会被合并为短章节。</p>"
            f"</body></html>"
        )
        book.add_item(chapter)
        items.append(chapter)

    book.toc = tuple(items)
    book.spine = ["nav", *items]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    output = BytesIO()
    epub.write_epub(output, book)
    return output.getvalue()


def test_split_chinese_chapters() -> None:
    text = """
第一章
雨落下来。

第二章：水产店
鱼在盆里打挺。

第三章
广播响起。
"""

    chapters = split_chapters(text)

    assert len(chapters) == 3
    assert chapters[0].title == "第一章"
    assert chapters[1].title == "第二章：水产店"
    assert "广播响起" in chapters[2].text


def test_split_chapter_one_english() -> None:
    text = """
Chapter One
The rain starts.

CHAPTER TWO
The shop opens.

Chapter 3
The phone rings.
"""

    chapters = split_chapters(text)

    assert len(chapters) == 3
    assert chapters[0].title == "Chapter One"
    assert chapters[1].title == "CHAPTER TWO"
    assert chapters[2].title == "Chapter 3"


def test_extract_epub_chapters() -> None:
    chapters = extract_epub_chapters(build_epub_bytes())

    assert len(chapters) == 3
    assert chapters[0].title == "第1章"
    assert "人物走进房间" in chapters[1].text
