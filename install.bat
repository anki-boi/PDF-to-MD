@echo off
setlocal

if not exist .venv (
  py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo Installation complete.
echo Run web app: .venv\Scripts\activate && python app.py
echo Run CLI: .venv\Scripts\activate && python cli.py C:\path\to\file.pdf
