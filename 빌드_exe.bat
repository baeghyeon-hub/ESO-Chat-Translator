@echo off
cd /d "%~dp0"

pip install pyinstaller --quiet

pyinstaller --onefile --noconsole --name "ESO_Translator" --add-data "eso_glossary.csv;." --add-data "config.json;." main.py

if exist "dist\ESO_Translator.exe" (
    copy "dist\ESO_Translator.exe" "ESO_Translator.exe"
)

pause
