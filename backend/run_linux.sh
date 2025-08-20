#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

python3 -m venv venv || true
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
cp ".env.example" ".env"
echo "[+] Created .env (fill COPERNICUSMARINE_PASSWORD / tokens)."
fi

python - <<'PY'
import os, subprocess
u=os.getenv('COPERNICUSMARINE_USERNAME'); p=os.getenv('COPERNICUSMARINE_PASSWORD')
if u and p:
try: subprocess.run(['copernicusmarine','login','--username',u,'--password',p,'--overwrite'],check=False)
except FileNotFoundError: print("[!] Install 'copernicusmarine' (pip).")
PY

export $(grep -v '^#' .env | xargs -d '\n' -I {} echo {})
exec uvicorn app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
