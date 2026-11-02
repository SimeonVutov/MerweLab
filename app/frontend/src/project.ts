export const scenarios = [
  { id: 'baseline', label: 'Current' },
  { id: 'scenario_a', label: 'V1' },
  { id: 'scenario_b', label: 'V2' },
] as const;

export type ScenarioId = (typeof scenarios)[number]['id'];
export type Mode = 'Explore' | 'Compare' | 'Weather';

export const layerGroups = [
  { label: 'Models', layers: [
    { id: 'context-buildings', label: 'Context buildings' },
    { id: 'scenario-buildings', label: 'Scenario buildings' },
    { id: 'site-surfaces', label: 'Site surfaces' },
    { id: 'trees', label: 'Trees' },
    { id: 'water', label: 'Water' },
  ] },
  { label: 'Environment', layers: [
    { id: 'aerial', label: 'Aerial imagery' },
    { id: 'elevation-colours', label: 'Elevation colours' },
    { id: 'study-boundary', label: 'Study boundary' },
  ] },
  { label: 'Morphology', layers: [
    { id: 'morphology-maps', label: 'Indicator maps' },
    { id: 'height', label: 'Building height' },
    { id: 'density', label: 'Density' },
    { id: 'svf', label: 'Sky view factor' },
    { id: 'hw', label: 'Height / width' },
  ] },
  { label: 'Wind & noise', layers: [
    { id: 'wind-speed', label: 'Wind speed' },
    { id: 'turbulence', label: 'Turbulence' },
    { id: 'wind-pressure', label: 'Pressure' },
    { id: 'wind-arrows', label: 'Direction arrows' },
    { id: 'streamlines-2d', label: '2D streamlines' },
    { id: 'streamlines-3d', label: '3D streamlines' },
    { id: 'noise', label: 'Noise' },
  ] },
  { label: 'Society', layers: [{ id: 'cbs', label: 'CBS neighbourhoods' }] },
  { label: 'Land use', layers: [
    { id: 'land-use-existing', label: 'Existing land use' },
    { id: 'land-use-optimized', label: 'Optimized land use' },
  ] },
  { label: 'Mobility', layers: [
    { id: 'roads', label: 'Road network' },
    { id: 'entrances', label: 'Entrances' },
    { id: 'garage-ramp', label: 'Garage ramp' },
  ] },
] as const;

export type LayerId = (typeof layerGroups)[number]['layers'][number]['id'];
