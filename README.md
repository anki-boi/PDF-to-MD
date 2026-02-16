# PDF to Markdown Chapters

A web app + CLI that lets you upload a PDF, **flattens it first**, extracts text, splits content into likely chapter files, and returns a ZIP containing:

- `*_flattened.pdf`
- `extraction-report.txt` (shows extraction method used)
- `01-<chapter>.md`, `02-<chapter>.md`, ...

You can also export directly to Anki `.apkg`, with optional chapter-based subdecks.

## Extraction strategy (better for obfuscated/edge-case PDFs)

1. Flatten PDF by rewriting pages into a new document.
2. Attempt embedded text extraction (`pypdf`).
3. If extracted text density is too low (default `< 25` chars/page), automatically fallback to OCR.
4. OCR engine: **Tesseract OCR** (`pytesseract` + `pypdfium2` rendering).

You can also force OCR for all pages in the UI or CLI.

## One-time installation scripts

### macOS / Linux

```bash
chmod +x install.sh
./install.sh
```

### Windows (CMD / PowerShell)

```bat
install.bat
```

## One-click drag-and-drop (Windows CMD)

Use `one_click_drag_drop.bat`:

1. Double click it once to verify it runs, or
2. Drag and drop a `.pdf` file onto `one_click_drag_drop.bat`.

It will auto-create `.venv`, install requirements, run conversion, and save the ZIP next to your PDF.

## Run web app

```bash
python app.py
```

Open `http://localhost:8000`.

## Run CLI directly

```bash
python cli.py /path/to/file.pdf
```

Optional examples:

```bash
python cli.py ./book.pdf --force-ocr
python cli.py ./book.pdf --ocr-lang eng --min-chars-per-page 30
python cli.py ./book.pdf --ai-cleanup --api-key "$OPENAI_API_KEY" --model gpt-4o-mini
python cli.py ./book.pdf --format apkg --deck-name "Pharma"
python cli.py ./book.pdf --format apkg --deck-name "Pharma" --no-subdecks
```

## Anki export

Use `--format apkg` to generate an Anki deck package:

- Default behavior creates chapter subdecks as `Deck Name::Chapter Title`.
- Disable subdecks with `--no-subdecks`.
- Set a custom root deck with `--deck-name`.

## Optional AI cleanup

After extraction, you can optionally send each chapter to an OpenAI-compatible chat-completions endpoint to clean OCR/extraction noise and polish readability.

## System dependencies for OCR

Install Tesseract binary on your system (examples):

- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- macOS (Homebrew): `brew install tesseract`
- Windows: install Tesseract OCR and ensure `tesseract.exe` is on PATH

Then Python dependencies from `requirements.txt` provide bindings and PDF rendering.

## Notes

- Chapter detection is heuristic-based (e.g., `Chapter 1: ...`, numbered headings, all-caps headings).
- AI cleanup is optional and requires API key + model.
- Default API endpoint: `https://api.openai.com/v1/chat/completions`.
