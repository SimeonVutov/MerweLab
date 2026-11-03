import { landUseMaps } from './types';
import type { LandUseLocation, LandUseMapId, LandUseSample } from './types';

export interface LandUseData {
  version: number;
  scope: string;
  bounds: [number, number, number, number];
  width: number;
  height: number;
  noData: number;
  classes: { code: number; label: string; colour: string }[];
  maps: { id: LandUseMapId; label: string; image: string; codes: string }[];
  summary: {
    areaSquareMetres: number;
    changedAreaSquareMetres: number;
    cellAreaSquareMetres: number;
    classes: { code: number; existingArea: number; optimizedArea: number }[];
  };
}

let manifestRequest: Promise<LandUseData> | undefined;
const codeRequests = new Map<LandUseMapId, Promise<Uint8Array>>();

function validateAsset(url: string, extension: string) {
  const pattern = new RegExp(`^/web/land-use/[\\w-]+\\.${extension}$`);
  if (!pattern.test(url)) throw new Error('Invalid land-use asset path');
}

async function fetchManifest(): Promise<LandUseData> {
  const response = await fetch('/web/land-use/manifest.json');
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Land-use assets are unavailable. Run preparation and restart the frontend.');
  }

  const data: LandUseData = await response.json();
  if (data.version !== 1 || data.scope !== 'shared-proposal') {
    throw new Error('Unsupported land-use manifest');
  }

  if (!Number.isInteger(data.width) || !Number.isInteger(data.height) || data.width < 1 || data.height < 1) {
    throw new Error('Invalid land-use grid dimensions');
  }

  if (data.bounds.length !== 4 || !data.bounds.every(Number.isFinite)
    || data.bounds[0] >= data.bounds[2] || data.bounds[1] >= data.bounds[3]) {
    throw new Error('Invalid land-use extent');
  }

  for (const { id } of landUseMaps) {
    const map = data.maps.find((item) => item.id === id);
    if (!map) throw new Error(`Missing land-use map: ${id}`);

    validateAsset(map.image, 'png');
    validateAsset(map.codes, 'uint8');
  }

  return data;
}

export function loadLandUse() {
  if (!manifestRequest) {
    manifestRequest = fetchManifest().catch((error: unknown) => {
      manifestRequest = undefined;
      throw error;
    });
  }
  return manifestRequest;
}

async function loadCodes(data: LandUseData, id: LandUseMapId) {
  let request = codeRequests.get(id);
  if (request) return request;

  const map = data.maps.find((item) => item.id === id)!;
  request = fetch(map.codes).then(async (response) => {
    if (!response.ok) throw new Error('Land-use cell values could not load');

    const codes = new Uint8Array(await response.arrayBuffer());
    const known = new Set([data.noData, ...data.classes.map((item) => item.code)]);
    if (codes.length !== data.width * data.height || codes.some((code) => !known.has(code))) {
      throw new Error('Invalid land-use class grid');
    }
    return codes;
  }).catch((error: unknown) => {
    codeRequests.delete(id);
    throw error;
  });

  codeRequests.set(id, request);
  return request;
}

export async function sampleLandUse(data: LandUseData, point: LandUseLocation): Promise<LandUseSample> {
  const [west, south, east, north] = data.bounds;
  const { longitude, latitude } = point;
  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) {
    return { outside: true, existing: null, optimized: null };
  }

  if (longitude < west || longitude >= east || latitude <= south || latitude > north) {
    return { outside: true, existing: null, optimized: null };
  }

  const column = Math.floor((longitude - west) / (east - west) * data.width);
  const row = Math.floor((north - latitude) / (north - south) * data.height);
  const index = row * data.width + column;
  const [existing, optimized] = await Promise.all([loadCodes(data, 'existing'), loadCodes(data, 'optimized')]);

  return {
    outside: false,
    existing: existing[index] === data.noData ? null : existing[index]!,
    optimized: optimized[index] === data.noData ? null : optimized[index]!,
  };
}
