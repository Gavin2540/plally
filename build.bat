@echo off
echo ============================================
echo   Building PlywoodPro Desktop Application
echo ============================================
echo.

echo [1/3] Installing PyInstaller...
pip install pyinstaller
echo.

echo [2/3] Creating required folders...
if not exist "assets" mkdir assets
if not exist "exports" mkdir exports
if not exist "backups" mkdir backups
echo.

echo [3/3] Building with PyInstaller...
pyinstaller build.spec --clean
echo.

echo ============================================
echo   Build complete!
echo   Output: dist\PlywoodPro\PlywoodPro.exe
echo ============================================
pause
