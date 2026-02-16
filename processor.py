from __future__ import annotations

import io
import tempfile
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CHAPTER_PATTERNS = [
    re.compile(r"^\s*(chapter\s+\d+[:\-.]?.*)$", re.IGNORECASE),
    re.compile(r"^\s*(\d+\.\s+[A-Z].*)$"),
    re.compile(r"^\s*([A-Z][A-Z\s]{6,})$"),
]


@dataclass
class Chunk:
    title: str
    text: str


@dataclass
class ExtractionDiagnostics:
    method: str
    avg_chars_per_page: int


def flatten_pdf(pdf_bytes: bytes) -> bytes:
    """Rewrites every page into a fresh PDF document to flatten structure."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def pdf_to_text_by_page(pdf_bytes: bytes) -> list[str]:
    """Extract text from embedded PDF text streams."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        pages.append((page.extract_text() or "").strip())
    return pages


def _ocr_text_by_page_tesseract(pdf_bytes: bytes, ocr_lang: str = "eng") -> list[str]:
    """OCR every page using Tesseract via rasterized PDF pages."""
    try:
        import pypdfium2 as pdfium
        import pytesseract
    except Exception as exc:
        raise RuntimeError(
            "OCR dependencies are missing. Install `pytesseract`, `pypdfium2`, and system `tesseract-ocr`."
        ) from exc

    doc = pdfium.PdfDocument(pdf_bytes)
    pages: list[str] = []

    for index in range(len(doc)):
        page = doc[index]
        bitmap = page.render(scale=2.0)
        pil_image = bitmap.to_pil()
        text = pytesseract.image_to_string(pil_image, lang=ocr_lang)
        pages.append(text.strip())
        page.close()

    doc.close()
    return pages


def _avg_characters_per_page(pages: Iterable[str]) -> int:
    pages_list = list(pages)
    if not pages_list:
        return 0
    total_chars = sum(len(re.sub(r"\s+", "", page)) for page in pages_list)
    return total_chars // len(pages_list)


def should_use_ocr(native_pages: list[str], min_chars_per_page: int) -> bool:
    return _avg_characters_per_page(native_pages) < min_chars_per_page


def extract_pages_with_fallback(
    pdf_bytes: bytes,
    force_ocr: bool = False,
    min_chars_per_page: int = 25,
    ocr_lang: str = "eng",
) -> tuple[list[str], ExtractionDiagnostics]:
    """Use embedded-text extraction first, and fall back to OCR for obfuscated/scanned PDFs."""
    native_pages = pdf_to_text_by_page(pdf_bytes)

    if not force_ocr and not should_use_ocr(native_pages, min_chars_per_page=min_chars_per_page):
        return native_pages, ExtractionDiagnostics(
            method="embedded-text",
            avg_chars_per_page=_avg_characters_per_page(native_pages),
        )

    ocr_pages = _ocr_text_by_page_tesseract(pdf_bytes, ocr_lang=ocr_lang)
    return ocr_pages, ExtractionDiagnostics(
        method="tesseract-ocr",
        avg_chars_per_page=_avg_characters_per_page(ocr_pages),
    )


def _find_heading(line: str) -> str | None:
    for pattern in CHAPTER_PATTERNS:
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return None


def split_into_chapters(pages: Iterable[str]) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_title = "Introduction"
    current_lines: list[str] = []

    for page in pages:
        for line in page.splitlines():
            heading = _find_heading(line)
            if heading and current_lines:
                chunks.append(Chunk(title=current_title, text="\n".join(current_lines).strip()))
                current_title = heading
                current_lines = []
            elif heading and not chunks and not current_lines:
                current_title = heading
            else:
                current_lines.append(line)

        current_lines.append("")

    if current_lines:
        chunks.append(Chunk(title=current_title, text="\n".join(current_lines).strip()))

    if not chunks:
        return [Chunk(title="Document", text="")]

    return chunks


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9\-_\s]", "", name).strip().lower()
    clean = re.sub(r"\s+", "-", clean)
    return clean[:80] or "chapter"


def _sanitize_deck_segment(name: str) -> str:
    clean = re.sub(r"[\r\n]+", " ", name).strip()
    clean = clean.replace("::", "-")
    return clean or "Untitled"


def _anki_deck_name(root_deck_name: str, chapter_title: str, use_subdecks: bool) -> str:
    root = _sanitize_deck_segment(root_deck_name)
    if not use_subdecks:
        return root
    chapter = _sanitize_deck_segment(chapter_title)
    return f"{root}::{chapter}"


def _ai_cleanup(text: str, api_key: str, model: str, endpoint: str) -> str:
    prompt = (
        "You are an expert technical editor. Clean OCR/PDF extraction noise, fix typos, "
        "and lightly polish readability without changing factual meaning. "
        "Preserve headings and code blocks. Return markdown only."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }
    import requests

    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def build_markdown_zip(
    source_name: str,
    pdf_bytes: bytes,
    ai_cleanup: bool = False,
    api_key: str | None = None,
    model: str | None = None,
    endpoint: str = "https://api.openai.com/v1/chat/completions",
    force_ocr: bool = False,
    ocr_lang: str = "eng",
    min_chars_per_page: int = 25,
) -> bytes:
    flattened = flatten_pdf(pdf_bytes)
    pages, diagnostics = extract_pages_with_fallback(
        flattened,
        force_ocr=force_ocr,
        min_chars_per_page=min_chars_per_page,
        ocr_lang=ocr_lang,
    )
    chapters = split_into_chapters(pages)

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        stem = Path(source_name).stem
        zf.writestr(f"{stem}_flattened.pdf", flattened)
        zf.writestr(
            "extraction-report.txt",
            f"method={diagnostics.method}\navg_chars_per_page={diagnostics.avg_chars_per_page}\n",
        )

        for index, chunk in enumerate(chapters, start=1):
            text = chunk.text
            if ai_cleanup:
                if not api_key or not model:
                    raise ValueError("API key and model are required for AI cleanup.")
                text = _ai_cleanup(text, api_key=api_key, model=model, endpoint=endpoint)

            title = _sanitize_filename(chunk.title)
            filename = f"{index:02d}-{title}.md"
            zf.writestr(filename, f"# {chunk.title}\n\n{text}\n")

    return archive.getvalue()


def build_anki_apkg(
    source_name: str,
    pdf_bytes: bytes,
    ai_cleanup: bool = False,
    api_key: str | None = None,
    model: str | None = None,
    endpoint: str = "https://api.openai.com/v1/chat/completions",
    force_ocr: bool = False,
    ocr_lang: str = "eng",
    min_chars_per_page: int = 25,
    deck_name: str = "PDF Imports",
    use_subdecks: bool = True,
) -> bytes:
    """Build an Anki .apkg package with one card per extracted chapter.

    When `use_subdecks` is enabled, each chapter is placed in its own subdeck:
    `<deck_name>::<chapter title>`.
    """
    try:
        import genanki
    except Exception as exc:
        raise RuntimeError("Anki export requires `genanki`. Install dependencies from requirements.txt.") from exc

    flattened = flatten_pdf(pdf_bytes)
    pages, _ = extract_pages_with_fallback(
        flattened,
        force_ocr=force_ocr,
        min_chars_per_page=min_chars_per_page,
        ocr_lang=ocr_lang,
    )
    chapters = split_into_chapters(pages)

    model_id = abs(hash(f"{Path(source_name).stem}-chapter-basic-model")) % (10**10)
    chapter_model = genanki.Model(
        model_id,
        "Chapter Basic",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
            }
        ],
    )

    decks_by_name: dict[str, object] = {}
    for chapter in chapters:
        text = chapter.text
        if ai_cleanup:
            if not api_key or not model:
                raise ValueError("API key and model are required for AI cleanup.")
            text = _ai_cleanup(text, api_key=api_key, model=model, endpoint=endpoint)

        deck_label = _anki_deck_name(deck_name, chapter.title, use_subdecks=use_subdecks)
        if deck_label not in decks_by_name:
            deck_id = abs(hash(deck_label)) % (10**10)
            decks_by_name[deck_label] = genanki.Deck(deck_id, deck_label)

        note = genanki.Note(
            model=chapter_model,
            fields=[chapter.title, text.replace("\n", "<br>")],
        )
        decks_by_name[deck_label].add_note(note)

    with tempfile.TemporaryDirectory() as tmp_dir:
        media_path = Path(tmp_dir) / "media.txt"
        media_path.write_text("", encoding="utf-8")
        package = genanki.Package(list(decks_by_name.values()))
        out_path = Path(tmp_dir) / "deck.apkg"
        package.write_to_file(str(out_path))
        return out_path.read_bytes()
