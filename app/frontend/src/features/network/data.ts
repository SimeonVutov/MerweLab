import { isNetworkPath, networkVariants } from './types';
import type { NetworkCollection, NetworkManifest } from './types';

let manifestRequest: Promise<NetworkManifest> | undefined;
const collections = new Map<string, Promise<NetworkCollection>>();

function validateAsset(url: string, extension: string) {
  if (!new RegExp(`^/web/network/[\\w-]+\\.${extension}$`).test(url)) {
    throw new Error('Invalid network asset path');
  }
}

async function fetchJson(url: string) {
  const response = await fetch(url);
  const contentType = response.headers.get('content-type') ?? '';
  if (!response.ok || !/json/.test(contentType)) {
    throw new Error('Network assets are unavailable. Prepare assets and restart the frontend.');
  }
  return response.json();
}

async function fetchManifest(): Promise<NetworkManifest> {
  const data: NetworkManifest = await fetchJson('/web/network/manifest.json');
  if (data.version !== 1 || data.bounds?.length !== 4 || !data.bounds.every(Number.isFinite)) {
    throw new Error('Invalid network manifest');
  }

  for (const scenario of ['scenario_a', 'scenario_b'] as const) {
    for (const { id } of networkVariants) {
      const entry = data.scenarios[scenario]?.[id];
      if (!entry) throw new Error('Incomplete network alternatives');

      validateAsset(entry.url, 'geojson');
      validateAsset(entry.figure, 'png');
      const indicators = Object.values(entry.summary.indicators);
      if (!indicators.every(Number.isFinite)) throw new Error('Invalid network indicators');
    }
  }

  for (const range of Object.values(data.ranges)) {
    if (range.length !== 2 || !range.every(Number.isFinite) || range[0]! > range[1]!) {
      throw new Error('Invalid network colour range');
    }
  }
  for (const figure of data.baseline.figures) validateAsset(figure.url, 'png');

  return data;
}

export function loadNetworkManifest() {
  if (!manifestRequest) {
    manifestRequest = fetchManifest().catch((error: unknown) => {
      manifestRequest = undefined;
      throw error;
    });
  }
  return manifestRequest;
}

export function validateNetworkCollection(data: NetworkCollection) {
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features) || data.features.length === 0) {
    throw new Error('Empty network feature collection');
  }

  const ids = new Set<string>();
  for (const feature of data.features) {
    if (feature.type !== 'Feature' || typeof feature.id !== 'string' || ids.has(feature.id)) {
      throw new Error('Invalid or duplicate network feature ID');
    }
    ids.add(feature.id);

    const points = feature.geometry.type === 'Point' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
    for (const point of points) {
      if (point.length !== 3 || !point.every(Number.isFinite)
        || Math.abs(point[0]!) > 180 || Math.abs(point[1]!) > 90) {
        throw new Error('Invalid network position');
      }
    }

    if (isNetworkPath(feature)) {
      const properties = feature.properties;
      if (feature.geometry.type !== 'LineString' || points.length < 2
        || !['walk + bike', 'car + walk', 'not built'].includes(properties.use)
        || ![properties.wind, properties.length, properties.residents_walking, properties.car_trips_per_day].every(Number.isFinite)) {
        throw new Error('Invalid network path');
      }
    } else if (feature.geometry.type !== 'Point' || !['entrance', 'garage_ramp'].includes(feature.properties.layer)) {
      throw new Error('Invalid network point');
    }
  }
}

export function loadNetworkCollection(url: string) {
  validateAsset(url, 'geojson');
  let request = collections.get(url);
  if (request) return request;

  request = fetchJson(url).then((data: NetworkCollection) => {
    validateNetworkCollection(data);
    return data;
  }).catch((error: unknown) => {
    collections.delete(url);
    throw error;
  });
  collections.set(url, request);
  return request;
}
