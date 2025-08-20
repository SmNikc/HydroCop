@echo off
REM --- ОБЯЗАТЕЛЬНО запускать из корня репозитория! ---
cd /d "%~dp0"
git add .
git commit -m "Auto push %date% %time%"
git push
pause
