export type WindMetric = 'speed' | 'turbulence' | 'pressure';
export type WindOverlay = 'arrows' | 'streamlines_2d' | 'streamlines_3d';

export interface WindOptions {
  metric: WindMetric | null;
  arrows: boolean;
  streamlines_2d: boolean;
  streamlines_3d: boolean;
  opacity: number;
}

export const initialWindOptions: WindOptions = {
  metric: null,
  arrows: false,
  streamlines_2d: false,
  streamlines_3d: false,
  opacity: 0.8,
};

export interface WindMetricInfo {
  label: string;
  units: string;
  range: [number, number];
  colours: string[];
  image: string;
  values: string;
  rawMaximum: number;
  outsideDisplayRange: number;
}

export interface WindSample {
  value: number | null;
  outsideRange: boolean;
  flagged: boolean;
}

export interface WindLocation {
  longitude: number;
  latitude: number;
}

export interface WindInfo {
  status: 'Off' | 'Loading' | 'Loaded' | 'Unavailable';
  metric: WindMetricInfo | null;
  flowLegend: WindMetricInfo | null;
  sample: WindSample | null;
  error: string | null;
  flaggedSamples: number;
}

export const initialWindInfo: WindInfo = {
  status: 'Off',
  metric: null,
  flowLegend: null,
  sample: null,
  error: null,
  flaggedSamples: 0,
};
