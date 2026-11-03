import type { ScenarioId } from '../../project';

export const networkVariants = [
    { id: 'balanced', label: 'Balanced' },
    { id: 'access_first', label: 'Accessibility first' },
    { id: 'green_first', label: 'Green first' },
    { id: 'no_wind', label: 'Without wind' },
] as const;

export type NetworkVariant = typeof networkVariants[number]['id'];
export type NetworkColour = 'use' | 'wind' | 'residents_walking' | 'car_trips_per_day';
export type NetworkPane = 'left' | 'right';
export type NetworkIndicator = 'access' | 'detour' | 'wind' | 'car' | 'green_loss' | 'cost';

export interface NetworkOptions {
    paths: boolean;
    entrances: boolean;
    ramp: boolean;
    candidates: boolean;
    variant: NetworkVariant;
    rightVariant: NetworkVariant | null;
    colour: NetworkColour;
    opacity: number;
    focusRequest: number;
}

export interface NetworkPath {
    type: 'Feature';
    id: string;
    geometry: { type: 'LineString'; coordinates: number[][] };
    properties: {
        layer: 'path';
        seg_id: string;
        kind: string;
        use: 'walk + bike' | 'car + walk' | 'not built';
        built: boolean;
        wind: number;
        residents_walking: number;
        car_trips_per_day: number;
        length: number;
    };
}

export interface NetworkPoint {
    type: 'Feature';
    id: string;
    geometry: { type: 'Point'; coordinates: number[] };
    properties: { layer: 'entrance' | 'garage_ramp'; building_id?: string };
}

export type NetworkFeature = NetworkPath | NetworkPoint;
export interface NetworkCollection {
    type: 'FeatureCollection';
    features: NetworkFeature[];
}

export interface NetworkSummary {
    method: string;
    built: string[];
    rampRd: number[];
    score: number;
    weights: Record<NetworkIndicator, number>;
    carTripsPerDay: number;
    bridgeBuilt: boolean;
    indicators: Record<NetworkIndicator, number>;
}

export interface NetworkEntry {
    url: string;
    figure: string;
    bounds: [number, number, number, number];
    summary: NetworkSummary;
}

export interface NetworkManifest {
    version: number;
    scenarios: Partial<Record<ScenarioId, Record<NetworkVariant, NetworkEntry>>>;
    bounds: [number, number, number, number];
    ranges: Record<Exclude<NetworkColour, 'use'>, [number, number]>;
    baseline: {
        accessibility: { facility: string; meanDistance: number; maximumDistance: number; walkMinutes: number }[];
        figures: { label: string; url: string }[];
    };
    sensitivity: {
        parameter: string;
        rows: { value: number; bridgeBuilt: boolean; built: string[]; indicators: Record<string, number> }[];
    }[];
}

export interface NetworkInfo {
    status: 'Off' | 'Loading' | 'Loaded' | 'Unavailable' | 'Error';
    selected: NetworkFeature | null;
    error: string | null;
}

export const initialNetworkOptions: NetworkOptions = {
    paths: false,
    entrances: false,
    ramp: false,
    candidates: false,
    variant: 'balanced',
    rightVariant: null,
    colour: 'use',
    opacity: 1,
    focusRequest: 0,
};

export const initialNetworkInfo: NetworkInfo = { status: 'Off', selected: null, error: null };

export function hasNetworkLayers(options: NetworkOptions) {
    return options.paths || options.entrances || options.ramp || options.candidates;
}

export function selectedNetworkVariant(options: NetworkOptions, pane: NetworkPane) {
    if (pane === 'right' && options.rightVariant) return options.rightVariant;
    return options.variant;
}

export function isNetworkPath(feature: NetworkFeature): feature is NetworkPath {
    return feature.properties.layer === 'path';
}
