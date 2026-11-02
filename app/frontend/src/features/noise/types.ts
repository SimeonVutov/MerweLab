export type NoisePeriod = 'D' | 'E' | 'N' | 'DEN';

export interface NoiseOptions {
  enabled: boolean;
  period: NoisePeriod;
  thresholdEnabled: boolean;
  threshold: number;
  opacity: number;
  retryRequest: number;
}

export interface NoiseLocation {
  longitude: number;
  latitude: number;
}

export interface NoiseClass {
  code: number;
  label: string;
  lower: number | null;
  upper: number | null;
  colour: string;
}

export interface ReceiverSample {
  id: string;
  distanceM: number;
  value: number | null;
}

export interface NoiseSample {
  band: NoiseClass | null;
  receiver: ReceiverSample | null;
  receiverStatus: 'Unavailable for V1' | 'Loading' | 'Loaded' | 'Unavailable';
}

export interface NoiseInfo {
  status: 'Off' | 'Loading' | 'Loaded' | 'Unavailable';
  error: string | null;
  sample: NoiseSample | null;
  classes: NoiseClass[];
}

export const noisePeriods: { id: NoisePeriod; label: string }[] = [
  { id: 'D', label: 'Day · 07–19' },
  { id: 'E', label: 'Evening · 19–23' },
  { id: 'N', label: 'Night · 23–07' },
  { id: 'DEN', label: 'Lden · day–evening–night' },
];

export const initialNoiseOptions: NoiseOptions = {
  enabled: false,
  period: 'DEN',
  thresholdEnabled: false,
  threshold: 55,
  opacity: 0.75,
  retryRequest: 0,
};

export const initialNoiseInfo: NoiseInfo = {
  status: 'Off',
  error: null,
  sample: null,
  classes: [],
};
