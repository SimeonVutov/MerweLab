import type { ScenarioId } from '../../project';
import { noisePeriods } from './types';
import type { NoiseClass, NoiseLocation, NoisePeriod, ReceiverSample } from './types';

export interface NoiseScenario {
    bounds: [number, number, number, number];
    width: number;
    height: number;
    maps: Record<NoisePeriod, { image: string }>;
    receivers: { url: string; count: number; valueField: string } | null;
}

export interface NoiseManifest {
    version: number;
    encoding: string;
    noData: number;
    nominalSpacingM: number;
    samplingHeightM: number;
    classes: NoiseClass[];
    mesh: {
        positions: string;
        st: string;
        indices: string;
        vertexCount: number;
        indexCount: number;
        originEcef: number[];
    };
    threshold: { minimum: number; maximum: number; step: number };
    scenarios: Record<ScenarioId, NoiseScenario>;
}

export interface NoiseReceiver extends NoiseLocation {
    id: string;
    levels: Record<NoisePeriod, number | null>;
}

let manifestRequest: Promise<NoiseManifest> | undefined;

export async function fetchNoiseAsset(url: string, signal?: AbortSignal) {
    if (!/^\/web\/noise\/[\w/.-]+$/.test(url) || url.includes('..')) {
        throw new Error('Invalid noise asset path');
    }

    const response = await fetch(url, { signal });
    if (!response.ok) {
        throw new Error(`Noise asset returned HTTP ${response.status}: ${url}`);
    }
    if (response.headers.get('content-type')?.includes('text/html')) {
        throw new Error('Noise assets are not being served. Restart the frontend server.');
    }

    if (url.endsWith('.gz') && !response.headers.get('content-encoding')?.includes('gzip')) {
        if (!response.body) {
            throw new Error('Empty noise asset');
        }
        return new Response(response.body.pipeThrough(new DecompressionStream('gzip')));
    }

    return response;
}

export function validateNoiseManifest(data: NoiseManifest) {
    if (data.version !== 1 || data.encoding !== 'uint8-class-code' || data.noData !== 0
        || data.classes?.length !== 11 || data.samplingHeightM !== 1.5
        || data.threshold?.minimum !== 35 || data.threshold.maximum !== 80 || data.threshold.step !== 5) {
        throw new Error('Unsupported noise dataset');
    }

    if (data.mesh?.originEcef?.length !== 3 || !data.mesh.originEcef.every(Number.isFinite)
        || !Number.isInteger(data.mesh.vertexCount) || data.mesh.vertexCount < 3
        || !Number.isInteger(data.mesh.indexCount) || data.mesh.indexCount < 3) {
        throw new Error('Invalid noise display mesh');
    }

    for (const [index, band] of data.classes.entries()) {
        if (band.code !== index + 1 || typeof band.label !== 'string'
            || !/^#[0-9a-f]{6}$/i.test(band.colour)) {
            throw new Error('Invalid noise class definitions');
        }

        const expectedLower = index === 0 ? null : 30 + index * 5;
        const expectedUpper = index === 10 ? null : 35 + index * 5;
        if (band.lower !== expectedLower || band.upper !== expectedUpper) {
            throw new Error('Unexpected noise class boundaries');
        }
    }

    for (const id of ['baseline', 'scenario_a', 'scenario_b'] as const) {
        const scenario = data.scenarios?.[id];
        if (!scenario || !Number.isInteger(scenario.width) || scenario.width < 1
            || !Number.isInteger(scenario.height) || scenario.height < 1
            || scenario.bounds?.length !== 4 || !scenario.bounds.every(Number.isFinite)) {
            throw new Error('Invalid noise map coverage');
        }

        const [west, south, east, north] = scenario.bounds;
        if (!(west < east && south < north)) {
            throw new Error('Invalid noise bounds');
        }

        for (const { id: period } of noisePeriods) {
            const image = scenario.maps?.[period]?.image;
            if (!image || !/^\/web\/noise\/[\w/.-]+\.png$/.test(image) || image.includes('..')) {
                throw new Error('Missing noise period image');
            }
        }

        if (id === 'scenario_a' && scenario.receivers !== null) {
            throw new Error('V1 receiver data is untrusted and must not be supplied');
        }
    }
}

async function fetchManifest(): Promise<NoiseManifest> {
    const response = await fetchNoiseAsset('/web/noise/manifest.json');
    const data: NoiseManifest = await response.json();
    validateNoiseManifest(data);

    return data;
}

export function loadNoiseManifest() {
    if (!manifestRequest) {
        manifestRequest = fetchManifest().catch((cause: unknown) => {
            manifestRequest = undefined;
            throw cause;
        });
    }

    return manifestRequest;
}

export function noiseCodeAt(
    codes: Uint8Array,
    data: NoiseScenario,
    point: NoiseLocation,
) {
    const [west, south, east, north] = data.bounds;
    if (point.longitude < west || point.longitude >= east
        || point.latitude <= south || point.latitude > north) {
        return 0;
    }

    const column = Math.floor((point.longitude - west) / (east - west) * data.width);
    const row = Math.floor((north - point.latitude) / (north - south) * data.height);
    return codes[row * data.width + column] ?? 0;
}

export function nearestNoiseReceiver(
    receivers: NoiseReceiver[],
    point: NoiseLocation,
    period: NoisePeriod,
): ReceiverSample | null {
    let nearest: NoiseReceiver | undefined;
    let nearestDistance = 75;
    const radians = Math.PI / 180;
    const latitude = point.latitude * radians;

    for (const receiver of receivers) {
        const deltaLatitude = (receiver.latitude - point.latitude) * radians;
        const deltaLongitude = (receiver.longitude - point.longitude) * radians;
        const haversine = Math.sin(deltaLatitude / 2) ** 2
            + Math.cos(latitude) * Math.cos(receiver.latitude * radians) * Math.sin(deltaLongitude / 2) ** 2;
        const distance = 6371008.8 * 2 * Math.asin(Math.sqrt(Math.min(1, haversine)));
        if (distance < nearestDistance) {
            nearest = receiver;
            nearestDistance = distance;
        }
    }

    if (!nearest) {
        return null;
    }

    return { id: nearest.id, distanceM: Math.round(nearestDistance), value: nearest.levels[period] };
}

export function validateNoiseReceivers(receivers: NoiseReceiver[], expectedCount: number) {
    if (!Array.isArray(receivers) || receivers.length !== expectedCount) {
        throw new Error('Incomplete noise receiver data');
    }

    const identifiers = new Set<string>();
    for (const receiver of receivers) {
        if (!receiver || typeof receiver.id !== 'string' || identifiers.has(receiver.id)
            || !Number.isFinite(receiver.longitude) || !Number.isFinite(receiver.latitude)) {
            throw new Error('Invalid noise receiver position');
        }

        for (const { id } of noisePeriods) {
            const value = receiver.levels?.[id];
            if (value !== null && (typeof value !== 'number' || !Number.isFinite(value))) {
                throw new Error('Invalid noise receiver level');
            }
        }

        identifiers.add(receiver.id);
    }
}
