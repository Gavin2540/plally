@echo off
echo ============================================
echo   PlywoodPro Release Builder
echo ============================================
echo.
set /p VERSION="Enter version number (example: 1.2.1): "
echo.

echo [1/4] Updating version number in updater.py...
powershell -command "(Get-Content utils\updater.py) -replace 'CURRENT_VERSION = \".*\"', 'CURRENT_VERSION = \"%VERSION%\"' | Set-Content utils\updater.py"
echo     Version set to %VERSION%
echo.

echo [2/4] Building executable...
call build.bat
echo.

echo [3/4] Creating release zip...
powershell -command "Compress-Archive -Path 'dist\PlywoodPro\*' -DestinationPath 'PlywoodPro_v%VERSION%.zip' -Force"
echo     Created PlywoodPro_v%VERSION%.zip
echo.

echo [4/4] Committing version bump and pushing tag to GitHub...
git add utils\updater.py
git commit -m "release: v%VERSION%"
git tag v%VERSION%
git push origin master --tags
echo.

echo ============================================
echo   BUILD DONE. Final step — do this manually:
echo.
echo   1. Open: github.com/Gavin2540/plally/releases/new
echo   2. Under "Choose a tag" select: v%VERSION%
echo   3. Title: PlywoodPro v%VERSION%
echo   4. Drag and drop: PlywoodPro_v%VERSION%.zip
echo   5. Click: Publish release
echo   6. Message your friend to open the app
echo      The update popup will appear automatically
echo ============================================
pause
