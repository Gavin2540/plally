@echo off
echo ============================================
echo   PlywoodPro Build Script v1.2
echo ============================================
echo.

echo [1/4] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller
echo.

echo [2/4] Backing up live database before clean build...
if exist "dist\PlywoodPro\plywoodpro.db" (
    copy "dist\PlywoodPro\plywoodpro.db" "plywoodpro_build_backup.db" >nul
    echo     Backed up existing database.
) else (
    echo     No existing database to backup.
)
echo.

echo [3/4] Building executable...
pyinstaller build.spec --clean --noconfirm
echo.

echo [4/4] Restoring live database...
if exist "plywoodpro_build_backup.db" (
    copy "plywoodpro_build_backup.db" "dist\PlywoodPro\plywoodpro.db" >nul
    del "plywoodpro_build_backup.db"
    echo     Database restored — your data is safe.
) else (
    echo     Fresh install.
)

echo.
echo ============================================
echo   BUILD COMPLETE: dist\PlywoodPro\PlywoodPro.exe
echo ============================================
pause
