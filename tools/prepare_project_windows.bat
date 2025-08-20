@echo off
setlocal
set STREAM_FILE=%~dp0published_code.txt
set ROOT=C:\Projects\GidroMeteo
if not exist "%ROOT%" mkdir "%ROOT%"
python "%~dp0apply_published_code_GidroMeteo.py" --input "%STREAM_FILE%" --root "%ROOT%" --eol crlf
endlocal
