import { AfterViewInit, Component, OnDestroy } from '@angular/core';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import OSM from 'ol/source/OSM';
import WMTS, { optionsFromCapabilities } from 'ol/source/WMTS';
import WMTSCapabilities from 'ol/format/WMTSCapabilities';
import { fromLonLat, toLonLat, transformExtent } from 'ol/proj';
import { defaults as defaultControls } from 'ol/control';
import { HydroMeteoService } from './hydrometeo.service';
import { Chart } from 'chart.js/auto';
import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';
import { Style, Fill, Stroke, RegularShape } from 'ol/style';

type RegionDef = { name: string; center: [number, number]; bbox: [number, number, number, number] };

@Component({
selector: 'app-hydrometeo-map',
templateUrl: './hydrometeo-map.component.html',
styleUrls: ['./hydrometeo-map.component.scss']
})
export class HydroMeteoMapComponent implements AfterViewInit, OnDestroy {
map!: Map;
base = new TileLayer({ source: new OSM() });
wmts?: TileLayer<WMTS>;
currentsSource = new VectorSource();
currentsLayer = new VectorLayer({ source: this.currentsSource });
currentsVisible = false;

apiOnline = false;
apiStatusText = 'проверка...';
activeLayerFilter = 'VHM0';
mode: 'waves' | 'temperature' = 'waves';
regionId: 'baltic' | 'north_sea' | 'mediterranean' | 'black_sea' | 'arctic' = 'baltic';
lat = 59.5;
lon = 24.8;

chart?: Chart;
seriesTitle = 'нет данных';
lastPoint: { lat: number, lon: number } | null = null;
lastValueFmt = '—';
lastUnit: string | null = null;

regions: Record<string, RegionDef> = {
baltic: { name: 'Балтийское море', center: [20, 59], bbox: [9, 53, 31, 66] },
north_sea: { name: 'Северное море', center: [4, 56], bbox: [-5, 50, 10, 62] },
mediterranean: { name: 'Средиземное море', center: [15, 40], bbox: [-6, 30, 36, 46] },
black_sea: { name: 'Чёрное море', center: [32, 43], bbox: [27, 40, 42, 47] },
arctic: { name: 'Арктика', center: [30, 75], bbox: [-20, 66, 60, 85] }
};

constructor(private api: HydroMeteoService) {}

async ngAfterViewInit(): Promise<void> {
this.map = new Map({
target: 'map',
layers: [this.base, this.currentsLayer],
controls: defaultControls(),
view: new View({
center: fromLonLat(this.regions[this.regionId].center),
zoom: 5
})
});

this.currentsLayer.setVisible(this.currentsVisible);
await this.checkApi();
await this.reloadWmts();

this.map.on('click', async (evt) => {
  const [lon, lat] = toLonLat(evt.coordinate);
  this.lat = lat; this.lon = lon;
  this.lastPoint = { lat, lon };
  try {
    if (this.mode === 'waves') {
      const data = await this.api.timeseriesWaves(lat, lon, 'VHM0');
      this.seriesTitle = 'Волны: VHM0 (значимая высота)';
      this.lastUnit = data.unit || 'm';
      this.lastValueFmt = data.values.length ? Number(data.values[data.values.length - 1]).toFixed(2) : '—';
      this.renderSingleSeries(data.times_utc, data.values, 'VHM0 (m)');
    } else {
      const data = await this.api.timeseriesPhysics(lat, lon, 'thetao');
      this.seriesTitle = 'Температура поверхности (thetao)';
      this.lastUnit = data.unit || '°C';
      this.lastValueFmt = data.values.length ? Number(data.values[data.values.length - 1]).toFixed(2) : '—';
      this.renderSingleSeries(data.times_utc, data.values, 'thetao (°C)');
    }
  } catch (e: any) {
    alert('Ошибка запроса тайм-серии: ' + e.message);
  }
});

this.map.on('moveend', () => {
  if (this.currentsVisible) this.updateCurrentsArrows();
});


}

ngOnDestroy(): void { if (this.chart) this.chart.destroy(); }

async checkApi() {
try {
const h = await this.api.health();
this.apiOnline = true;
this.apiStatusText = OK (waves=${h.datasets?.waves}, phy=${h.datasets?.physics});
} catch {
this.apiOnline = false;
this.apiStatusText = 'нет связи с backend';
}
}

async reloadWmts(): Promise<void> {
const txt = await fetch(this.api.getWmtsCapabilitiesUrl()).then(r => r.text());
const parser = new WMTSCapabilities();
const caps: any = parser.read(txt);

const layers: any[] = (caps.Contents?.Layer || []);
const pick = (preferred: string) => {
  let cand = layers.find(l =>
    String(l.Identifier || '').toUpperCase().includes(preferred.toUpperCase()) &&
    ((l.Title || '').toUpperCase().includes('BALTIC') || (l.Abstract || '').toUpperCase().includes('BALTIC'))
  );
  if (!cand) cand = layers.find(l => String(l.Identifier || '').toUpperCase().includes(preferred.toUpperCase()));
  return cand;
};

const layer = pick(this.activeLayerFilter) || layers[0];
if (!layer) throw new Error('WMTS: слои не обнаружены');

const options = optionsFromCapabilities(caps, {
  layer: layer.Identifier,
  matrixSet: (layer.TileMatrixSetLink?.[0]?.TileMatrixSet) || (caps.Contents?.TileMatrixSet?.[0]?.Identifier),
});

if (options && (options as any).urls && (options as any).urls.length) {
  (options as any).urls = [ this.api.getWmtsTileUrlTemplate()
    .replace('{Layer}', encodeURIComponent(layer.Identifier))
    .replace('{Style}', encodeURIComponent((layer.Style?.[0]?.Identifier) || 'default'))
    .replace('{Format}', encodeURIComponent((layer.Format?.[0]) || 'image/png'))
    .replace('{TileMatrixSet}', encodeURIComponent((options as any).matrixSet))
  ];
}

const source = new WMTS(options as any);
if (this.wmts) this.wmts.setSource(source);
else {
  this.wmts = new TileLayer({ source });
  this.map.addLayer(this.wmts);
}


}

renderSingleSeries(labels: string[], values: number[], label: string) {
const ctx = (document.getElementById('seriesChart') as HTMLCanvasElement).getContext('2d')!;
if (this.chart) this.chart.destroy();
this.chart = new Chart(ctx, {
type: 'line',
data: { labels, datasets: [{ label, data: values, fill: false }] },
options: { parsing: false, normalized: true, scales: { x: { ticks: { maxTicksLimit: 8 } } } }
});
}

async toggleCurrents() {
this.currentsVisible = !this.currentsVisible;
this.currentsLayer.setVisible(this.currentsVisible);
if (this.currentsVisible) await this.updateCurrentsArrows();
else this.currentsSource.clear();
}

async updateCurrentsArrows() {
try {
const extent3857 = this.map.getView().calculateExtent(this.map.getSize());
const [minx, miny, maxx, maxy] = transformExtent(extent3857, 'EPSG:3857', 'EPSG:4326');
const step = 8;
const grid: any = await this.api.currentsGrid(miny, minx, maxy, maxx, step);

  this.currentsSource.clear();
  const lons: number[] = grid.lons;
  const lats: number[] = grid.lats;
  const U: number[] = grid.u;
  const V: number[] = grid.v;

  const nx = lons.length;
  const ny = lats.length;

  for (let iy = 0; iy < ny; iy++) {
    for (let ix = 0; ix < nx; ix++) {
      const idx = iy * nx + ix;
      const u = U[idx], v = V[idx];
      if (!isFinite(u) || !isFinite(v)) continue;

      const lon = lons[ix], lat = lats[iy];
      const speed = Math.sqrt(u * u + v * v);
      const dir = Math.atan2(v, u);

      const feature = new Feature({ geometry: new Point(fromLonLat([lon, lat])) });
      const size = 6 + Math.min(18, speed * 20);
      const style = new Style({
        image: new RegularShape({
          points: 3,
          radius: size,
          rotation: -dir,
          angle: 0,
          fill: new Fill({ color: 'rgba(0,0,0,0)' }),
          stroke: new Stroke({ color: '#1f5fbf', width: 2 })
        })
      });
      feature.setStyle(style);
      this.currentsSource.addFeature(feature);
    }
  }
} catch (e: any) {
  console.error('Ошибка построения стрелок течений:', e.message);
}

}
}
