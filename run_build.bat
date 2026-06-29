@echo off
echo === Compilation ClubMessenger ===
python -m pip install -r requirements.txt
pyinstaller build_desktop.spec

echo === Construction de l'installateur NSIS ===
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi

echo.
echo === Terminé ===
echo Exécutable   : dist\ClubMessenger.exe
echo Installateur : Setup_ClubMessenger_v%VERSION%.exe
pause
