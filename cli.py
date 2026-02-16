from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from processor import build_markdown_zip


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a PDF to flattened PDF + chapter markdown ZIP."
    )
    parser.add_argument("pdf", help="Path to input PDF")
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR for all pages")
    parser.add_argument("--ocr-lang", default="eng", help="Tesseract language code (default: eng)")
    parser.add_argument(
        "--min-chars-per-page",
        type=int,
        default=25,
        help="Fallback to OCR when embedded extraction avg chars/page is below this threshold",
    )
    parser.add_argument("--ai-cleanup", action="store_true", help="Enable AI cleanup")
    parser.add_argument("--api-key", help="API key for AI cleanup")
    parser.add_argument("--model", help="Model for AI cleanup")
    parser.add_argument(
        "--endpoint",
        default="https://api.openai.com/v1/chat/completions",
        help="OpenAI-compatible chat completions endpoint",
    )
    parser.add_argument("--output", help="Output ZIP file path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pdf_path = Path(args.pdf)

    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        print(f"Error: '{pdf_path}' is not a valid PDF path.")
        return 1

    if args.ai_cleanup and (not args.api_key or not args.model):
        print("Error: --api-key and --model are required when --ai-cleanup is enabled.")
        return 1

    output_path = Path(args.output) if args.output else pdf_path.with_name(
        f"{pdf_path.stem}-chapters-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    )

    zip_bytes = build_markdown_zip(
        source_name=pdf_path.name,
        pdf_bytes=pdf_path.read_bytes(),
        ai_cleanup=args.ai_cleanup,
        api_key=args.api_key,
        model=args.model,
        endpoint=args.endpoint,
        force_ocr=args.force_ocr,
        ocr_lang=args.ocr_lang,
        min_chars_per_page=args.min_chars_per_page,
    )

    output_path.write_bytes(zip_bytes)
    print(f"Done: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
