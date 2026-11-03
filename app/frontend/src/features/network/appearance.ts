import { isNetworkPath } from './types';
import type { NetworkColour, NetworkFeature, NetworkManifest, NetworkOptions, NetworkPath } from './types';

export const networkColours = {
  walking: '#70b496',
  cars: '#d3a36a',
  candidate: '#9ba7a0',
  entrance: '#7da7d1',
  ramp: '#cd7d75',
  selected: '#f1d36b',
};

export const intensityColours = ['#418b9d', '#6bb49c', '#b4ca8f', '#e0c47b', '#d48a65', '#b65759'];
export const networkColourModes: { id: NetworkColour; label: string }[] = [
  { id: 'use', label: 'Path use' },
  { id: 'wind', label: 'Wind exposure · relative' },
  { id: 'residents_walking', label: 'Assigned residents' },
  { id: 'car_trips_per_day', label: 'Estimated car trips / day' },
];

export function networkFeatureVisible(feature: NetworkFeature, options: NetworkOptions) {
  if (isNetworkPath(feature)) return feature.properties.built ? options.paths : options.candidates;
  if (feature.properties.layer === 'entrance') return options.entrances;
  return options.ramp;
}

export function networkPathColour(path: NetworkPath, mode: NetworkColour, data: NetworkManifest) {
  if (!path.properties.built) return networkColours.candidate;
  if (mode === 'use') return path.properties.use === 'car + walk' ? networkColours.cars : networkColours.walking;

  // Both comparison panes use one global scale across every saved alternative.
  const [minimum, maximum] = data.ranges[mode];
  const value = path.properties[mode];
  const fraction = maximum === minimum ? 0 : (value - minimum) / (maximum - minimum);
  const index = Math.max(0, Math.min(intensityColours.length - 1, Math.floor(fraction * intensityColours.length)));
  return intensityColours[index]!;
}
