from processor import _anki_deck_name, should_use_ocr, split_into_chapters


def test_split_into_chapters_detects_chapter_heading():
    pages = [
        "Chapter 1: Intro\nhello world",
        "Chapter 2: Next\nmore text",
    ]
    chunks = split_into_chapters(pages)
    assert len(chunks) == 2
    assert chunks[0].title.lower().startswith("chapter 1")
    assert "hello" in chunks[0].text
    assert chunks[1].title.lower().startswith("chapter 2")


def test_split_into_chapters_fallback_title():
    chunks = split_into_chapters(["no heading\njust text"])
    assert len(chunks) == 1
    assert chunks[0].title == "Introduction"


def test_should_use_ocr_when_embedded_text_is_too_sparse():
    pages = ["", "   ", "x"]
    assert should_use_ocr(pages, min_chars_per_page=5) is True


def test_should_not_use_ocr_when_embedded_text_is_sufficient():
    pages = ["this is enough text", "this is enough text too"]
    assert should_use_ocr(pages, min_chars_per_page=5) is False


def test_anki_deck_name_uses_subdecks_when_enabled():
    assert _anki_deck_name("Pharma", "Chapter 1: Intro", use_subdecks=True) == "Pharma::Chapter 1: Intro"


def test_anki_deck_name_without_subdecks_uses_root_only():
    assert _anki_deck_name("Pharma", "Chapter 1: Intro", use_subdecks=False) == "Pharma"
