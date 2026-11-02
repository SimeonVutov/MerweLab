import type { ScenarioId } from '../../project';

export interface MorphologyOptions {
  layers: Record<string, { enabled: boolean; opacity: number }>;
  order: string[];
  focusRequest: number;
}

export function hasMorphologyLayers(options: MorphologyOptions) {
  return Object.values(options.layers).some((layer) => layer.enabled);
}

export interface MorphologyLayer {
  id: string;
  indicator: string;
  scenario: string;
  url: string;
  bounds: [number, number, number, number];
  legend: {
    categories: string[] | null;
    colours: string[] | null;
    limits: number[] | null;
    cmap: string | null;
    gradient: string[] | null;
  };
}

export interface MorphologyData {
  version: number;
  kind: string;
  layers: MorphologyLayer[];
}

export const morphologyIndicators = [
  ['factor1_height_classes_extended', 'Height classes'],
  ['factor2_density_classes_extended', 'Building density'],
  ['factor3_hw_50m_classes_extended', 'H/W · 50 m dominant class'],
  ['factor3_hw_classes_extended', 'H/W · 25 m open spaces'],
  ['factor4_svf_classes_extended', 'SVF classes'],
  ['factor4_svf_continuous_extended', 'SVF · continuous colours'],
  ['factor5_heat_ventilation_risk_extended', 'Morphological heat/ventilation risk'],
  ['factor5_priority', 'Morphological risk priority'],
  ['factor6_final_risk_extended', 'Vulnerability-adjusted risk'],
  ['factor6_priority', 'Vulnerability-adjusted priority'],
  ['factor6_priority_change', 'Priority change after vulnerability adjustment'],
  ['svf_change_vs_existing_extended', 'SVF change versus Existing'],
  ['factor6_age_45plus_introduction', 'Neighbourhood age 45+ share'],
  ['introduction-buildings', 'Introduction · boundary and buildings'],
  ['4_universal_50_x_50_m_analytical_grid', 'Introduction · universal 50 m grid'],
] as const;

export const initialMorphologyOptions: MorphologyOptions = {
  layers: Object.fromEntries(morphologyIndicators.map(([id]) => [id, { enabled: false, opacity: 0.7 }])),
  order: morphologyIndicators.map(([id]) => id),
  focusRequest: 0,
};

let request: Promise<MorphologyData> | undefined;

export function selectMorphologyLayer(data: MorphologyData, indicator: string, scenario: ScenarioId) {
  if (indicator === 'introduction-buildings') {
    const names = {
      baseline: '1_research_boundary_and_existing_buildings',
      scenario_a: '2_development_site_with_v1',
      scenario_b: '3_development_site_with_v2',
    };
    return data.layers.find((layer) => layer.indicator === names[scenario]);
  }

  return data.layers.find((layer) => layer.indicator === indicator
    && (layer.scenario === scenario || layer.scenario === 'shared' || layer.scenario === 'introduction'));
}

async function fetchManifest(): Promise<MorphologyData> {
  const response = await fetch('/web/morphology/manifest.json');
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Morphology assets are unavailable. Restart the frontend server.');
  }

  const data: MorphologyData = await response.json();
  if (data.version !== 1 || data.kind !== 'rendered-imagery' || !Array.isArray(data.layers)) {
    throw new Error('Invalid morphology manifest');
  }

  for (const layer of data.layers) {
    if (!/^\/web\/morphology\/[\w.-]+\.png$/.test(layer.url) || layer.url.includes('..')
      || layer.bounds?.length !== 4 || !layer.bounds.every(Number.isFinite)) {
      throw new Error('Invalid morphology image placement');
    }
  }

  return data;
}

export function loadMorphology() {
  if (!request) {
    request = fetchManifest().catch((error: unknown) => {
      request = undefined;
      throw error;
    });
  }

  return request;
}
