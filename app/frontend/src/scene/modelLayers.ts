import { Axis, Cartesian2, Cartesian3, Model, PrimitiveCollection, Transforms } from 'cesium';
import type { Viewer } from 'cesium';
import type { ScenarioId } from '../project';

type Group = 'shared' | ScenarioId;
export type LoadStatus = 'Loading' | 'Loaded' | 'Unavailable';
export interface ModelStatus {
  context: LoadStatus;
  scenario: LoadStatus;
}
interface ModelManifest {
  version: number;
  placement: { origin_ecef_m: number[]; local_frame: string };
  models: Record<Group, { id: string; url: string }[]>;
}

async function loadManifest(signal: AbortSignal): Promise<ModelManifest> {
  const response = await fetch('/web/buildings/manifest.json', { signal });
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Prepared buildings manifest is unavailable');
  }
  const manifest: ModelManifest = await response.json();
  if (manifest.version !== 1 || manifest.placement?.local_frame !== 'ENU'
    || manifest.placement.origin_ecef_m?.length !== 3
    || !manifest.placement.origin_ecef_m.every(Number.isFinite)) {
    throw new Error('Unsupported model placement');
  }
  const groups: Group[] = ['shared', 'baseline', 'scenario_a', 'scenario_b'];
  const urlPattern = /^\/web\/buildings\/[\w.-]+\.glb$/;
  for (const group of groups) {
    if (!Array.isArray(manifest.models?.[group]) || !manifest.models[group].length
      || !manifest.models[group].every((asset) => urlPattern.test(asset.url) && !asset.url.includes('..'))) {
      throw new Error(`Missing or invalid buildings assets for ${group}`);
    }
  }
  return manifest;
}

export function createModelLayers(
  viewer: Viewer,
  onStatus: (status: ModelStatus) => void,
) {
  const collection = viewer.scene.primitives.add(new PrimitiveCollection());
  const abort = new AbortController();
  const manifest = loadManifest(abort.signal);
  const groups = new Map<Group, Model[]>();
  const pending = new Map<Group, Promise<Model[]>>();
  let disposed = false;
  let activeScenario: ScenarioId | null = null;
  let contextVisible = true;
  let scenarioVisible = true;
  let status: ModelStatus = {
    context: 'Loading', scenario: 'Loading',
  };

  function publish(update: Partial<ModelStatus>) {
    if (disposed) return;
    status = { ...status, ...update };
    onStatus(status);
  }

  function updateVisibility() {
    for (const [group, models] of groups) {
      for (const model of models) {
        model.show = group === 'shared' ? contextVisible
          : group === activeScenario && scenarioVisible;
      }
    }
    viewer.scene.requestRender();
  }

  function loadGroup(group: Group): Promise<Model[]> {
    const existing = pending.get(group);
    if (existing) return existing;
    const request = manifest.then(async (data) => {
      if (disposed) return [];
      const matrix = Transforms.eastNorthUpToFixedFrame(Cartesian3.fromArray(data.placement.origin_ecef_m));
      const assets = data.models[group];
      const results = await Promise.allSettled(assets.map((asset) => Model.fromGltfAsync({
        url: asset.url,
        modelMatrix: matrix,
        // Blender already encodes ENU as (east, up, -north); only undo Y-up.
        upAxis: Axis.Y,
        forwardAxis: Axis.X,
        backFaceCulling: true,
        // Fixed ambient lighting keeps separate WebGL viewers visually comparable.
        environmentMapOptions: { enabled: false },
        show: false,
      }).then((model) => {
        model.imageBasedLighting.imageBasedLightingFactor = new Cartesian2(1, 0);
        return model;
      })));
      const models = results.flatMap((result) => result.status === 'fulfilled' ? [result.value] : []);
      if (disposed || results.some((result) => result.status === 'rejected')) {
        models.forEach((model) => model.destroy());
        if (!disposed) throw new Error(`Could not load ${group} buildings`);
        return [];
      }
      models.forEach((model) => collection.add(model));
      groups.set(group, models);
      updateVisibility();
      return models;
    }).catch((cause: unknown) => {
      pending.delete(group);
      throw cause;
    });
    pending.set(group, request);
    return request;
  }

  void loadGroup('shared').then(() => publish({ context: 'Loaded' })).catch((cause: unknown) => {
    if (disposed) return;
    console.error(`Context buildings failed to load`, cause);
    publish({ context: 'Unavailable' });
  });

  return {
    setScenario(scenario: ScenarioId) {
      activeScenario = scenario;
      updateVisibility();
      publish({ scenario: groups.has(scenario) ? 'Loaded' : 'Loading' });
      void loadGroup(scenario).then(() => {
        if (activeScenario === scenario) publish({ scenario: 'Loaded' });
      }).catch((cause: unknown) => {
        if (disposed || activeScenario !== scenario) return;
        console.error(`Scenario buildings failed to load`, cause);
        publish({ scenario: 'Unavailable' });
      });
    },
    setVisibility(context: boolean, scenario: boolean) {
      contextVisible = context;
      scenarioVisible = scenario;
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
