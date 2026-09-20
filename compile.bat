@echo off
setlocal enabledelayedexpansion

:: Path to our bundled python, so the user doesn't need anything installed
set PYTHON_EXE=python-portable\python.exe
set PYFILE=gta-sa.py

echo ==========================================
echo  PyInstaller Build
echo ==========================================
echo.

:: Keep things isolated - don't let the portable python pick up
:: packages or paths from whatever is installed on this machine
set PYTHONNOUSERSITE=1
set PYTHONPATH=
set PYTHONHOME=

if not exist "%PYTHON_EXE%" (
    echo ERROR: Portable python not found at "%PYTHON_EXE%".
    echo Make sure the "python-portable" folder is next to this script.
    pause
    exit /b 1
)

if not exist "%PYFILE%" (
    echo ERROR: "%PYFILE%" doesn't exist.
    pause
    exit /b 1
)

echo Cleaning up old builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "gta-sa.spec" del /q "gta-sa.spec"

echo.
echo Building "%PYFILE%"...

:: Bundle the img folder if it's there
set add_data_opt=
if exist "img" (
    set add_data_opt=--add-data "img;img"
    echo   - img folder found, it will be bundled into the exe.
) else (
    echo   - WARNING: no img folder, background and icons won't be included.
)

:: Use img\icon.ico as the exe icon if it exists
set icon_opt=
if exist "img\icon.ico" (
    set icon_opt=--icon="img\icon.ico"
    echo   - icon.ico found, applying it to the exe.
)

:: pywin32 stuff, needed for the taskbar icon to work properly
set hidden_imports=--hidden-import=win32gui --hidden-import=win32api --hidden-import=win32con --hidden-import=win32timezone

echo   - Compiling, this can take a minute or two...

"%PYTHON_EXE%" -m PyInstaller --noconsole --onefile --clean --noconfirm !add_data_opt! !icon_opt! !hidden_imports! "%PYFILE%"

if errorlevel 1 (
    echo.
    echo *** Build failed. ***
    pause
    exit /b 1
)

echo.
echo =========================================================
echo Done! The exe is in the "dist" folder.
echo =========================================================
pause
exit /b 0