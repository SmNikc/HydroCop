import os
import json
import tempfile
import subprocess
import datetime as dt
from typing import Optional, List, Tuple

import httpx
import numpy as np
import xarray as xr
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv

=== Load environment ===

load_dotenv()
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
WMTS_BASE = os.getenv("CMDS_WMTS_BASE", "https://wmts.marine.copernicus.eu/teroWmts
")
CM_USER = os.getenv("COPERNICUSMARINE_USERNAME")
CM_PASS = os.getenv("COPERNICUSMARINE_PASSWORD")
DATASET_WAV = os.getenv("CMDS_DATASET_WAV", "cmems_mod_bal_wav_anfc_PT1H-i")
DATASET_PHY = os.getenv("CMDS_DATASET_PHY", "cmems_mod_bal_phy_anfc_PT15M-i")
CACHE_DIR = os.getenv("CACHE_DIR", "./data/cache")

os.makedirs(CACHE_DIR, exist_ok=True)

app = FastAPI(title="HydroMeteo CMDS API", version="1.1.1")

CORS (без пустых значений)

app.add_middleware(
CORSMiddleware,
allow_origins=[""], # ограничьте при необходимости
allow_credentials=True,
allow_methods=[""],
allow_headers=["*"],
)

=== Models ===

class TimeSeriesRequest(BaseModel):
dataset: str
variable: str
lat: float
lon: float
depth: Optional[float] = None
start_utc: Optional[str] = None
end_utc: Optional[str] = None

class TimeSeriesResponse(BaseModel):
times_utc: List[str]
values: List[float]
unit: Optional[str] = None
meta: dict

class CurrentsGridRequest(BaseModel):
min_lon: float
min_lat: float
max_lon: float
max_lat: float
time_utc: Optional[str] = None
step: int = 6
depth: Optional[float] = None

class CurrentsGridResponse(BaseModel):
lons: List[float]
lats: List[float]
u: List[float]
v: List[float]
meta: dict

=== Helpers ===

def _ensure_login_if_possible() -> None:
if not (CM_USER and CM_PASS):
return
try:
subprocess.run(
["copernicusmarine", "login", "--username", CM_USER, "--password", CM_PASS, "--overwrite"],
check=False, capture_output=True, text=True
)
except FileNotFoundError:
pass

def subset_with_cli(dataset_id: str, variables: List[str],
xmin: float, xmax: float, ymin: float, ymax: float,
t_start: Optional[str], t_end: Optional[str]) -> str:
fd, out_path = tempfile.mkstemp(prefix="subset", suffix=".nc", dir=CACHE_DIR)
os.close(fd)
cmd = ["copernicusmarine", "subset", "-i", dataset_id]
for v in variables:
cmd += ["-v", v]
cmd += ["-x", str(xmin), "-X", str(xmax), "-y", str(ymin), "-Y", str(ymax)]
if t_start: cmd += ["-t", t_start]
if t_end: cmd += ["-T", t_end]
cmd += ["-o", os.path.dirname(out_path), "-f", os.path.basename(out_path), "--file-format", "netcdf"]
try:
subprocess.run(cmd, check=True, capture_output=True, text=True)
except FileNotFoundError:
raise HTTPException(status_code=500, detail="Не найден CLI 'copernicusmarine'. Установите пакет и выполните login.")
except subprocess.CalledProcessError as e:
raise HTTPException(status_code=502, detail=(e.stderr or e.stdout or "Ошибка copernicusmarine subset"))
return out_path

def _detect_coords(ds: xr.Dataset) -> Tuple[str, str, str]:
time_candidates = ["time", "t"]
lat_candidates = ["latitude", "lat", "y"]
lon_candidates = ["longitude", "lon", "x"]
def pick(cands, present):
for n in cands:
if n in present: return n
return None
present = set(list(ds.dims) + list(ds.coords))
t = pick(time_candidates, present)
la = pick(lat_candidates, present)
lo = pick(lon_candidates, present)
if not (t and la and lo):
for v in ds.variables:
var = ds[v]
std = getattr(var, "standard_name", "")
if std == "latitude": la = v
elif std == "longitude": lo = v
if not la or not lo:
raise ValueError("Невозможно определить имена координат (lat/lon)")
if not t:
for cand in time_candidates:
if cand in ds:
t = cand
break
if not t:
raise ValueError("Невозможно определить имя временной оси")
return t, la, lo

def _to_timeseries_json(da: xr.DataArray) -> TimeSeriesResponse:
times_iso: List[str] = []
time_dim = da.dims[0]
for ts in da[time_dim].values:
if hasattr(ts, "astype"):
py_dt = np.datetime64(ts).astype("datetime64[ms]").astype(dt.datetime)
else:
py_dt = ts
times_iso.append(py_dt.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z"))
vals = da.values.astype(float).tolist()
unit = da.attrs.get("units")
return TimeSeriesResponse(times_utc=times_iso, values=vals, unit=unit, meta={})

@app.on_event("startup")
async def on_startup():
_ensure_login_if_possible()

@app.get("/health", response_class=PlainTextResponse)
async def health():
info = {"wmts": WMTS_BASE, "datasets": {"waves": DATASET_WAV, "physics": DATASET_PHY}, "cm_user": bool(CM_USER)}
return json.dumps(info, ensure_ascii=False)

@app.get("/wmts/capabilities")
async def wmts_capabilities():
params = {"service": "WMTS", "version": "1.0.0", "request": "GetCapabilities"}
auth = (CM_USER, CM_PASS) if (CM_USER and CM_PASS) else None
async with httpx.AsyncClient(timeout=60.0) as client:
r = await client.get(WMTS_BASE, params=params, auth=auth)
if r.status_code != 200:
raise HTTPException(status_code=r.status_code, detail=f"WMTS GetCapabilities error: {r.text[:400]}")
return Response(content=r.content, media_type="application/xml")

@app.get("/wmts/tile")
async def wmts_tile(request: Request):
query = str(request.url.query)
url = WMTS_BASE + ("?" + query if query else "")
auth = (CM_USER, CM_PASS) if (CM_USER and CM_PASS) else None
async with httpx.AsyncClient(timeout=120.0) as client:
r = await client.get(url, auth=auth)
if r.status_code != 200:
raise HTTPException(status_code=r.status_code, detail=f"WMTS tile error: {r.text[:400]}")
media = r.headers.get("Content-Type", "image/png")
return Response(content=r.content, media_type=media)

@app.post("/api/timeseries", response_model=TimeSeriesResponse)
async def timeseries(req: TimeSeriesRequest):
dataset = req.dataset.lower().strip()
if dataset not in ("waves", "physics"):
raise HTTPException(status_code=400, detail="dataset должен быть 'waves' или 'physics'")
ds_id = DATASET_WAV if dataset == "waves" else DATASET_PHY
variables = [req.variable]
eps = 0.05
xmin, xmax = req.lon - eps, req.lon + eps
ymin, ymax = req.lat - eps, req.lat + eps
t_end = req.end_utc or dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
t_start = req.start_utc or (dt.datetime.utcnow() - dt.timedelta(hours=48)).replace(microsecond=0).isoformat() + "Z"
nc_path = _subset_with_cli(ds_id, variables, xmin, xmax, ymin, ymax, t_start, t_end)
try:
ds = xr.open_dataset(nc_path)
tname, laname, loname = _detect_coords(ds)
da = ds[req.variable].sel({laname: req.lat, loname: req.lon}, method="nearest")
ts = _to_timeseries_json(da)
ts.meta = {"dataset_id": ds_id, "variable": req.variable, "lat": float(req.lat),
"lon": float(req.lon), "t_start": t_start, "t_end": t_end}
return ts
except KeyError:
raise HTTPException(status_code=400, detail=f"Переменная '{req.variable}' не найдена в '{ds_id}'")
except Exception as e:
raise HTTPException(status_code=500, detail=f"Ошибка чтения NetCDF: {e}")
finally:
try: os.remove(nc_path)
except OSError: pass

@app.post("/api/currents-grid", response_model=CurrentsGridResponse)
async def currents_grid(req: CurrentsGridRequest):
ds_id = DATASET_PHY
variables = ["uo", "vo"]
t = req.time_utc or dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
t_dt = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
t_start = (t_dt - dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
t_end = (t_dt + dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
nc_path = _subset_with_cli(ds_id, variables, req.min_lon, req.max_lon, req.min_lat, req.max_lat, t_start, t_end)
try:
ds = xr.open_dataset(nc_path)
, lat_name, lon_name = detect_coords(ds)
u = ds["uo"].isel({"time": 0})
v = ds["vo"].isel({"time": 0})
lats = u[lat_name].values
lons = u[lon_name].values
step = max(1, int(req.step))
lat_idx = np.arange(0, len(lats), step)
lon_idx = np.arange(0, len(lons), step)
U = u.values[np.ix(lat_idx, lon_idx)]
V = v.values[np.ix(lat_idx, lon_idx)]
return CurrentsGridResponse(
lons=[float(x) for x in lons[lon_idx]],
lats=[float(y) for y in lats[lat_idx]],
u=[float(val) for val in U.flatten()],
v=[float(val) for val in V.flatten()],
meta={"dataset_id": ds_id, "time": t}
)
except Exception as e:
raise HTTPException(status_code=500, detail=f"Ошибка выборки течений: {e}")
finally:
try: os.remove(nc_path)
except OSError: pass
