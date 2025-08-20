import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class HydroMeteoService {
// Базовый URL backend (можно переопределить через window.HYDROMETEO_API)
baseUrl: string = (window as any).HYDROMETEO_API || 'http://localhost:8000
';

getWmtsCapabilitiesUrl(): string {
return ${this.baseUrl}/wmts/capabilities;
}

getWmtsTileUrlTemplate(): string {
// Прокси WMTS-тайлов через backend
return ${this.baseUrl}/wmts/tile? +
'SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&Layer={Layer}&Style={Style}&' +
'Format={Format}&TileMatrixSet={TileMatrixSet}&TileMatrix={TileMatrix}&' +
'TileRow={TileRow}&TileCol={TileCol}&Time={Time}';
}

async fetchJson<T = any>(url: string, init?: RequestInit): Promise<T> {
const r = await fetch(url, init);
if (!r.ok) {
const text = await r.text();
throw new Error(${r.status} ${r.statusText}: ${text});
}
return r.json();
}

async postJson<T = any>(url: string, body: any): Promise<T> {
const r = await fetch(url, {
method: 'POST',
headers: {'Content-Type': 'application/json'},
body: JSON.stringify(body)
});
if (!r.ok) {
const text = await r.text();
throw new Error(${r.status} ${text});
}
return r.json();
}

timeseriesWaves(lat: number, lon: number, variable = 'VHM0', start?: string, end?: string) {
return this.postJson(${this.baseUrl}/api/timeseries, {
dataset: 'waves', variable, lat, lon, start_utc: start, end_utc: end
});
}

timeseriesPhysics(lat: number, lon: number, variable = 'thetao', start?: string, end?: string) {
return this.postJson(${this.baseUrl}/api/timeseries, {
dataset: 'physics', variable, lat, lon, start_utc: start, end_utc: end
});
}

currentsGrid(minLat: number, minLon: number, maxLat: number, maxLon: number, step = 8) {
return this.postJson(${this.baseUrl}/api/currents-grid, {
min_lat: minLat, min_lon: minLon, max_lat: maxLat, max_lon: maxLon, step
});
}
}
