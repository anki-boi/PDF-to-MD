@echo off
setlocal

if "%~1"=="" (
  echo Drag and drop a PDF file onto this script.
  pause
  exit /b 1
)

if /I not "%~x1"==".pdf" (
  echo Please drop a .pdf file.
  pause
  exit /b 1
)

if not exist .venv (
  py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
python cli.py "%~1"

if errorlevel 1 (
  echo Processing failed.
) else (
  echo Success.
)

pause
