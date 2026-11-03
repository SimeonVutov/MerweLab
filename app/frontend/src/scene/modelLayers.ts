import { Axis, Cartesian2, Cartesian3, Model, PrimitiveCollection, Transforms } from 'cesium';
import type { GroundPrimitive, Viewer } from 'cesium';
import type { ScenarioId } from '../project';
import { loadWaterSurface } from './waterSurface';

type Renderable = Model | GroundPrimitive;

type Group = 'shared' | 'water' | ScenarioId;
export type LoadStatus = 'Loading' | 'Loaded' | 'Unavailable';

export interface ModelStatus {
  context: LoadStatus;
  scenario: LoadStatus;
  water?: LoadStatus;
}

interface ModelManifest {
  version: number;
  placement: {
    origin_ecef_m: number[];
    local_frame: string;
  };
  models: Record<Group, { id: string; url: string }[]>;
}

async function loadManifest(dataset: 'buildings' | 'surfaces', signal: AbortSignal): Promise<ModelManifest> {
  const response = await fetch(`/web/${dataset}/manifest.json`, { signal });
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
    throw new Error(`Prepared ${dataset} manifest is unavailable`);
  }

  const manifest: ModelManifest = await response.json();
  if (manifest.version !== 1 || manifest.placement?.local_frame !== 'ENU'
    || manifest.placement.origin_ecef_m?.length !== 3
    || !manifest.placement.origin_ecef_m.every(Number.isFinite)) {
    throw new Error('Unsupported model placement');
  }

  const groups: Group[] = ['shared', 'baseline', 'scenario_a', 'scenario_b'];
  if (dataset === 'surfaces') {
    groups.push('water');
  }

  const urlPattern = new RegExp(`^/web/${dataset}/[\\w.-]+\\.glb$`);
  for (const group of groups) {
    if (!Array.isArray(manifest.models?.[group]) || (!manifest.models[group].length && !(dataset === 'surfaces' && group === 'shared'))
      || !manifest.models[group].every((asset) => urlPattern.test(asset.url) && !asset.url.includes('..'))) {
      throw new Error(`Missing or invalid ${dataset} assets for ${group}`);
    }
  }

  return manifest;
}

export function createModelLayers(
  viewer: Viewer,
  dataset: 'buildings' | 'surfaces',
  onStatus: (status: ModelStatus) => void,
) {
  const collection = viewer.scene.primitives.add(new PrimitiveCollection());
  const abort = new AbortController();
  const manifest = loadManifest(dataset, abort.signal);
  const groups = new Map<Group, Renderable[]>();
  const pending = new Map<Group, Promise<Renderable[]>>();
  let disposed = false;
  let activeScenario: ScenarioId | null = null;
  let contextVisible = true;
  let scenarioVisible = true;
  let waterVisible = true;
  let status: ModelStatus = {
    context: 'Loading',
    scenario: 'Loading',
    ...(dataset === 'surfaces' ? { water: 'Loading' } : {}),
  };

  function publish(update: Partial<ModelStatus>) {
    if (disposed) {
      return;
    }

    status = { ...status, ...update };
    onStatus(status);
  }

  function updateVisibility() {
    for (const [group, models] of groups) {
      for (const model of models) {
        if (group === 'shared') {
          model.show = contextVisible;
        } else if (group === 'water') {
          model.show = waterVisible;
        } else {
          model.show = group === activeScenario && scenarioVisible;
        }
      }
    }

    viewer.scene.requestRender();
  }

  async function loadWaterGroup(): Promise<Renderable[]> {
    const water = await loadWaterSurface(abort.signal);
    if (disposed) {
      water.destroy();
      return [];
    }

    collection.add(water);
    groups.set('water', [water]);
    updateVisibility();

    return [water];
  }

  async function loadModels(data: ModelManifest, group: Group): Promise<Renderable[]> {
    const matrix = Transforms.eastNorthUpToFixedFrame(Cartesian3.fromArray(data.placement.origin_ecef_m));
    const assets = data.models[group];

    const results = await Promise.allSettled(assets.map((asset) => Model.fromGltfAsync({
      url: asset.url,
      modelMatrix: matrix,
      // Blender already encodes ENU as (east, up, -north); only undo Y-up.
      upAxis: Axis.Y,
      forwardAxis: Axis.X,
      backFaceCulling: dataset === 'buildings',
      // Fixed ambient lighting keeps separate WebGL viewers visually comparable.
      environmentMapOptions: { enabled: false },
      show: false,
    }).then((model) => {
      model.imageBasedLighting.imageBasedLightingFactor = new Cartesian2(1, 0);
      return model;
    })));

    const models = results.flatMap((result) => result.status === 'fulfilled' ? [result.value] : []);
    // A group owns its models only after every asset succeeds; release partial or late results.
    if (disposed || results.some((result) => result.status === 'rejected')) {
      models.forEach((model) => model.destroy());
      if (!disposed) {
        throw new Error(`Could not load ${group} ${dataset}`);
      }

      return [];
    }

    models.forEach((model) => collection.add(model));
    groups.set(group, models);
    updateVisibility();

    return models;
  }

  function loadGroup(group: Group): Promise<Renderable[]> {
    const existing = pending.get(group);
    if (existing) {
      return existing;
    }

    const request = manifest.then(async (data) => {
      if (disposed) {
        return [];
      }

      if (dataset === 'surfaces' && group === 'water') {
        return loadWaterGroup();
      }

      return loadModels(data, group);
    }).catch((cause: unknown) => {
      pending.delete(group);
      throw cause;
    });

    pending.set(group, request);
    return request;
  }

  void loadGroup('shared').then(() => publish({ context: 'Loaded' })).catch((cause: unknown) => {
    if (disposed) {
      return;
    }

    console.error(`Context ${dataset} failed to load`, cause);
    publish({ context: 'Unavailable' });
  });

  if (dataset === 'surfaces') {
    void loadGroup('water').then(() => publish({ water: 'Loaded' })).catch((cause: unknown) => {
      if (disposed) {
        return;
      }

      console.error('Water failed to load', cause);
      publish({ water: 'Unavailable' });
    });
  }

  return {
    setScenario(scenario: ScenarioId) {
      activeScenario = scenario;
      updateVisibility();
      publish({ scenario: groups.has(scenario) ? 'Loaded' : 'Loading' });

      void loadGroup(scenario).then(() => {
        if (activeScenario === scenario) {
          publish({ scenario: 'Loaded' });
        }
      }).catch((cause: unknown) => {
        if (disposed || activeScenario !== scenario) {
          return;
        }

        console.error(`Scenario ${dataset} failed to load`, cause);
        publish({ scenario: 'Unavailable' });
      });
    },
    setVisibility(context: boolean, scenario: boolean, water = true) {
      contextVisible = context;
      scenarioVisible = scenario;
      waterVisible = water;
      updateVisibility();
    },
    dispose() {
      disposed = true;
      abort.abort();
      viewer.scene.primitives.remove(collection);
    },
  };
}

export type ModelLayers = ReturnType<typeof createModelLayers>;
