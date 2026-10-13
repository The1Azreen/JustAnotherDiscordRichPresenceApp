@echo off
REM Build a standalone Windows exe in dist\ with PyInstaller.
REM Your config.ini, credentials and game database are NOT bundled:
REM place them next to the exe (it reads them from its own folder).
REM Optional pandas extras (pyarrow, numba, ...) are excluded to keep the exe small.

SETLOCAL
cd /d "%~dp0"

echo Installing build tools...
python -m pip install -r requirements.txt pyinstaller pillow || exit /b 1

if not exist assets\app.ico python tools\make_icon.py || exit /b 1

echo Building JustAnotherDRP.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name JustAnotherDRP ^
    --icon "%~dp0assets\app.ico" ^
    --add-data "%~dp0fonts;fonts" ^
    --add-data "%~dp0assets;assets" ^
    --specpath build ^
    --exclude-module matplotlib --exclude-module IPython --exclude-module PIL ^
    --exclude-module scipy --exclude-module pytest ^
    --exclude-module pyarrow --exclude-module numba --exclude-module llvmlite ^
    --exclude-module sqlalchemy --exclude-module tqdm --exclude-module fsspec --exclude-module lxml ^
    main.py || exit /b 1

copy /y config.ini.example dist\config.ini.example >nul

echo.
echo Done: dist\JustAnotherDRP.exe
echo Copy config.ini (and games_database.xlsx / credentials.json if you use them) next to the exe.
