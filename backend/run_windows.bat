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

python -c "import os,subprocess;u=os.getenv('COPERNICUSMARINE_USERNAME');p=os.getenv('COPERNICUSMARINE_PASSWORD');
(subprocess.run(['copernicusmarine','login','--username',u,'--password',p,'--overwrite'],check=False) if (u and p) else None)"

set API_HOST=0.0.0.0
set API_PORT=8000

uvicorn app.main:app --host %API_HOST% --port %API_PORT% --reload
endlocal
