Python-only comments
FastAPI backend for HydroMeteo CMDS with ice support (SIC/SIT).
Uses Copernicus Marine Toolbox CLI to subset NetCDF and serves time series and grids.

import os
import io
import json
import math
import tempfile
import subprocess
import datetime as dt
from typing import Optional, List, Tuple, Dict

import httpx
import numpy as np
import xarray as xr
from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
WMTS_BASE = os.getenv("CMDS_WMTS_BASE", "https://wmts.marine.copernicus.eu/teroWmts
")
CM_USER = os.getenv("COPERNICUSMARINE_USERNAME")
CM_PASS = os.getenv("COPERNICUSMARINE_PASSWORD")
DATASET_WAV = os.getenv("CMDS_DATASET_WAV", "cmems_mod_bal_wav_anfc_PT1H-i")
DATASET_PHY = os.getenv("CMDS_DATASET_PHY", "cmems_mod_bal_phy_anfc_PT15M-i")
DATASET_ICE = os.getenv("CMDS_DATASET_ICE", DATASET_PHY)
CACHE_DIR = os.getenv("CACHE_DIR", "./data/cache")
os.makedirs(CACHE_DIR, exist_ok=True)

app = FastAPI(title="HydroMeteo CMDS API", version="1.1.0")

app.add_middleware(
CORSMiddleware,
allow_origins=[""],
allow_credentials=True,
allow_methods=[""],
allow_headers=["*"],
)

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

class IceSeriesResponse(BaseModel):
times_utc: List[str]
siconc: List[Optional[float]]
sithick: List[Optional[float]]
drift_speed: Optional[List[Optional[float]]] = None
drift_dir_deg: Optional[List[Optional[float]]] = None
units: Dict[str, str] = {}
meta: dict = {}

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
raise HTTPException(status_code=500, detail="CLI 'copernicusmarine' not found. Install and login.")
except subprocess.CalledProcessError as e:
raise HTTPException(status_code=502, detail=f"copernicusmarine subset error: {e.stderr or e.stdout}")
return out_path

def _detect_coords(ds: xr.Dataset) -> Tuple[str, str, str]:
time_names = ["time", "t"]
lat_names = ["latitude", "lat", "y"]
lon_names = ["longitude", "lon", "x"]
def pick(cands, present):
for n in cands:
if n in present: return n
return None
dims = set(list(ds.dims) + list(ds.coords))
t = pick(time_names, dims)
la = pick(lat_names, dims)
lo = pick(lon_names, dims)
if not (t and la and lo):
for v in ds.variables:
var = ds[v]
if getattr(var, "standard_name", "") == "latitude": la = v
if getattr(var, "standard_name", "") == "longitude": lo = v
if not la or not lo: raise ValueError("Unable to detect lat/lon names")
if not t:
for cand in ["time", "ocean_time"]:
if cand in ds: t = cand
if not t: raise ValueError("Unable to detect time axis")
return t, la, lo

def _to_iso_list(time_values) -> List[str]:
out = []
for ts in time_values:
if hasattr(ts, "astype"):
py = np.datetime64(ts).astype("datetime64[ms]").astype(dt.datetime)
else:
py = ts
out.append(py.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z"))
return out

def _pick_var(ds: xr.Dataset, candidates: List[str]) -> Optional[str]:
names = set(ds.variables)
for c in candidates:
if c in names: return c
lowered = {v.lower(): v for v in ds.variables}
for c in candidates:
if c.lower() in lowered: return lowered[c.lower()]
return None

@app.on_event("startup")
async def on_startup():
_ensure_login_if_possible()

@app.get("/health", response_class=PlainTextResponse)
async def health():
info = {
"wmts": WMTS_BASE,
"datasets": {"waves": DATASET_WAV, "physics": DATASET_PHY, "ice": DATASET_ICE},
"cm_user": bool(CM_USER),
}
return json.dumps(info, ensure_ascii=False)

@app.get("/wmts/capabilities")
async def wmts_capabilities():
params = {"service":"WMTS", "version":"1.0.0", "request":"GetCapabilities"}
auth = (CM_USER, CM_PASS) if (CM_USER and CM_PASS) else None
async with httpx.AsyncClient(timeout=60.0) as client:
r = await client.get(WMTS_BASE, params=params, auth=auth)
if r.status_code != 200:
raise HTTPException(status_code=r.status_code, detail=f"WMTS GetCapabilities error: {r.text[:200]}")
return Response(content=r.content, media_type="application/xml")

@app.get("/wmts/tile")
async def wmts_tile(request: Request):
query = str(request.url.query)
url = WMTS_BASE + ("?" + query if query else "")
auth = (CM_USER, CM_PASS) if (CM_USER and CM_PASS) else None
async with httpx.AsyncClient(timeout=120.0) as client:
r = await client.get(url, auth=auth)
if r.status_code != 200:
raise HTTPException(status_code=r.status_code, detail=f"WMTS tile error: {r.text[:200]}")
media = r.headers.get("Content-Type", "image/png")
return Response(content=r.content, media_type=media)

@app.post("/api/timeseries", response_model=TimeSeriesResponse)
async def timeseries(req: TimeSeriesRequest):
dataset = req.dataset.lower()
if dataset not in ("waves", "physics", "ice"):
raise HTTPException(status_code=400, detail="dataset must be 'waves'|'physics'|'ice'")
ds_id = DATASET_WAV if dataset == "waves" else (DATASET_ICE if dataset == "ice" else DATASET_PHY)
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
times_iso = _to_iso_list(da[da.dims[0]].values)
vals = da.values.astype(float).tolist()
unit = da.attrs.get("units", None)
return TimeSeriesResponse(times_utc=times_iso, values=vals, unit=unit, meta={
"dataset_id": ds_id, "variable": req.variable, "lat": float(req.lat), "lon": float(req.lon),
"t_start": t_start, "t_end": t_end
})
except KeyError:
raise HTTPException(status_code=400, detail=f"Variable {req.variable} not found in {ds_id}")
except Exception as e:
raise HTTPException(status_code=500, detail=f"NetCDF read error: {e}")
finally:
try: os.remove(nc_path)
except OSError: pass

@app.post("/api/currents-grid", response_model=CurrentsGridResponse)
async def currents_grid(req: CurrentsGridRequest):
ds_id = DATASET_PHY
variables = ["uo", "vo"]
t = req.time_utc or dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
t_start = (dt.datetime.fromisoformat(t.replace("Z","+00:00")) - dt.timedelta(minutes=1)).isoformat().replace("+00:00","Z")
t_end = (dt.datetime.fromisoformat(t.replace("Z","+00:00")) + dt.timedelta(minutes=1)).isoformat().replace("+00:00","Z")
nc_path = _subset_with_cli(ds_id, variables, req.min_lon, req.max_lon, req.min_lat, req.max_lat, t_start, t_end)
try:
ds = xr.open_dataset(nc_path)
, la, lo = detect_coords(ds)
u = ds["uo"].isel(time=0)
v = ds["vo"].isel(time=0)
lats = u[la].values
lons = u[lo].values
lat_idx = np.arange(0, len(lats), max(1, req.step))
lon_idx = np.arange(0, len(lons), max(1, req.step))
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
raise HTTPException(status_code=500, detail=f"Currents grid error: {e}")
finally:
try: os.remove(nc_path)
except OSError: pass

@app.post("/api/ice-timeseries", response_model=IceSeriesResponse)
async def ice_timeseries(lat: float = Body(...), lon: float = Body(...),
start_utc: Optional[str] = Body(None), end_utc: Optional[str] = Body(None),
dataset_id: Optional[str] = Body(None)):
ds_id = dataset_id or DATASET_ICE
eps = 0.05
xmin, xmax = lon - eps, lon + eps
ymin, ymax = lat - eps, lat + eps
t_end = end_utc or dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
t_start = start_utc or (dt.datetime.utcnow() - dt.timedelta(hours=48)).replace(microsecond=0).isoformat() + "Z"

cand_sic = ["siconc", "sic", "ice_concentration", "sea_ice_area_fraction"]
cand_sit = ["sithick", "sit", "ice_thickness", "sea_ice_thickness"]
cand_siu = ["siu", "uice", "sivelu", "si_vel_u"]
cand_siv = ["siv", "vice", "siveln", "si_vel_v"]

variables = list({cand_sic[0], cand_sit[0], cand_siu[0], cand_siv[0]})
nc_path = _subset_with_cli(ds_id, variables, xmin, xmax, ymin, ymax, t_start, t_end)

try:
    ds = xr.open_dataset(nc_path)
    tname, laname, loname = _detect_coords(ds)
    name_sic = _pick_var(ds, cand_sic)
    name_sit = _pick_var(ds, cand_sit)
    name_siu = _pick_var(ds, cand_siu)
    name_siv = _pick_var(ds, cand_siv)

    if not (name_sic or name_sit):
        raise HTTPException(status_code=400, detail="SIC/SIT variables not found in dataset")

    times = None
    out = IceSeriesResponse(times_utc=[], siconc=[], sithick=[], units={}, meta={})
    if name_sic:
        da = ds[name_sic].sel({laname: lat, loname: lon}, method="nearest")
        times = da[da.dims[0]].values
        values = da.values.astype(float)
        unit = (da.attrs.get("units") or "").strip()
        if not unit or unit in ("1", "fraction"):
            values = values * 100.0
            unit_out = "%"
        elif unit in ("%", "percent"):
            unit_out = "%"
        else:
            unit_out = unit
        out.siconc = values.tolist()
        out.units["siconc"] = unit_out

    if name_sit:
        da2 = ds[name_sit].sel({laname: lat, loname: lon}, method="nearest")
        if times is None: times = da2[da2.dims[0]].values
        out.sithick = da2.values.astype(float).tolist()
        out.units["sithick"] = (da2.attrs.get("units") or "m")

    drift_speed = None
    drift_dir = None
    if name_siu and name_siv:
        dau = ds[name_siu].sel({laname: lat, loname: lon}, method="nearest")
        dav = ds[name_siv].sel({laname: lat, loname: lon}, method="nearest")
        if times is None: times = dau[dau.dims[0]].values
        u = dau.values.astype(float)
        v = dav.values.astype(float)
        drift_speed = np.sqrt(u*u + v*v)
        # Direction: oceanographic (to) in degrees, atan2(v,u)
        drift_dir = (np.degrees(np.arctan2(v, u)) + 360.0) % 360.0
        out.drift_speed = drift_speed.tolist()
        out.drift_dir_deg = drift_dir.tolist()
        out.units["drift_speed"] = "m s-1"
        out.units["drift_dir_deg"] = "degree"

    out.times_utc = _to_iso_list(times)
    out.meta = {
        "dataset_id": ds_id, "lat": float(lat), "lon": float(lon),
        "t_start": t_start, "t_end": t_end,
        "sic_var": name_sic, "sit_var": name_sit, "siu_var": name_siu, "siv_var": name_siv
    }
    return out

except HTTPException:
    raise
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Ice time series error: {e}")
finally:
    try: os.remove(nc_path)
    except OSError: pass
