@echo off
echo ============================================
echo  PlywoodPro Build Script
echo ============================================
echo.
echo Step 1: Installing/updating dependencies...
pip install -r requirements.txt
pip install pyinstaller
echo.
echo Step 2: Cleaning previous build...
if exist dist\PlywoodPro rmdir /s /q dist\PlywoodPro
if exist build\build rmdir /s /q build\build
echo.
echo Step 3: Building executable...
pyinstaller build.spec --clean --noconfirm
echo.
echo Step 4: Copying database schema to dist...
if not exist dist\PlywoodPro\db mkdir dist\PlywoodPro\db
copy db\schema.sql dist\PlywoodPro\db\
echo.
echo ============================================
echo  BUILD COMPLETE
echo  Location: dist\PlywoodPro\PlywoodPro.exe
echo  Share the entire dist\PlywoodPro\ folder
echo ============================================
pause
