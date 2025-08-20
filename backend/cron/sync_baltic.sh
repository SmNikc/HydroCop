#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

source venv/bin/activate || true
export $(grep -v '^#' .env | xargs -d '\n' -I {} echo {})

TODAY=$(date -u +"%Y%m%d")
OUTDIR="${CACHE_DIR:-./data/cache}"
mkdir -p "$OUTDIR"

echo "[*] Sync Baltic PHYS..."
copernicusmarine subset -i "${CMDS_DATASET_PHY:-cmems_mod_bal_phy_anfc_PT15M-i}"
-v uo -v vo -v thetao -x 9 -X 31 -y 53 -Y 66
-t "$(date -u -d '2 days ago' +%Y-%m-%dT%H:%M:%SZ)"
-T "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
-o "$OUTDIR" -f "baltic_phy_${TODAY}.nc" --file-format netcdf

echo "[*] Sync Baltic WAV..."
copernicusmarine subset -i "${CMDS_DATASET_WAV:-cmems_mod_bal_wav_anfc_PT1H-i}"
-v VHM0 -v VMDR -v VTPK -x 9 -X 31 -y 53 -Y 66
-t "$(date -u -d '2 days ago' +%Y-%m-%dT%H:%M:%SZ)"
-T "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
-o "$OUTDIR" -f "baltic_wav_${TODAY}.nc" --file-format netcdf

echo "[*] Sync Baltic ICE..."
copernicusmarine subset -i "${CMDS_DATASET_ICE:-cmems_mod_bal_phy_anfc_PT15M-i}"
-v siconc -v sithick -x 9 -X 31 -y 53 -Y 66
-t "$(date -u -d '2 days ago' +%Y-%m-%dT%H:%M:%SZ)"
-T "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
-o "$OUTDIR" -f "baltic_ice_${TODAY}.nc" --file-format netcdf

echo "[OK] Baltic sync done."
