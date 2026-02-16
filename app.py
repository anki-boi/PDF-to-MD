from __future__ import annotations

import io
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file

from processor import build_markdown_zip

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/process")
def process_pdf():
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "Upload a PDF file first."}), 400

    ai_cleanup = request.form.get("ai_cleanup") == "true"
    api_key = request.form.get("api_key") or None
    model = request.form.get("model") or None
    endpoint = request.form.get("endpoint") or "https://api.openai.com/v1/chat/completions"

    force_ocr = request.form.get("force_ocr") == "true"
    ocr_lang = request.form.get("ocr_lang") or "eng"
    min_chars_per_page = int(request.form.get("min_chars_per_page") or 25)

    try:
        zip_bytes = build_markdown_zip(
            source_name=uploaded.filename,
            pdf_bytes=uploaded.read(),
            ai_cleanup=ai_cleanup,
            api_key=api_key,
            model=model,
            endpoint=endpoint,
            force_ocr=force_ocr,
            ocr_lang=ocr_lang,
            min_chars_per_page=min_chars_per_page,
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_name = f"{uploaded.filename.rsplit('.', 1)[0]}-chapters-{ts}.zip"
    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=out_name,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
