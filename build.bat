@echo off
chcp 65001 >nul
echo === Подготовка окружения ===

:: Создаем виртуальное окружение, если его нет
if not exist .venv (
    python -m venv .venv
)

:: Активируем и ставим зависимости
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo === Сборка ZipperGUI.exe ===

:: Собираем EXE.
:: Ключ --paths "src" говорит PyInstaller, где искать наш пакет zipper.
:: Точка входа - main.py.
pyinstaller --noconfirm --clean --onefile --windowed ^
    --name "ZipperGUI" ^
    --paths "src" ^
    main.py

echo.
echo Готово! Файл находится в папке dist\ZipperGUI.exe
pause