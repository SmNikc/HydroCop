@echo off
setlocal enabledelayedexpansion
set ROOT=%~dp0
cd /d %ROOT%

if not exist venv (
py -3 -m venv venv
)
call venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist ".env" (
copy ".env.example" ".env"
echo [+] Created .env (fill COPERNICUSMARINE_PASSWORD / tokens).
)

python - <<PY
import os, subprocess
u=os.getenv('COPERNICUSMARINE_USERNAME'); p=os.getenv('COPERNICUSMARINE_PASSWORD')
if u and p:
try: subprocess.run(['copernicusmarine','login','--username',u,'--password',p,'--overwrite'],check=False)
except FileNotFoundError: print("[!] Install 'copernicusmarine' (pip).")
PY

set API_HOST=0.0.0.0
set API_PORT=8000
uvicorn app.main:app --host %API_HOST% --port %API_PORT% --reload
endlocal
