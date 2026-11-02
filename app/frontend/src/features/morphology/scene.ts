import { ImageryLayer, Rectangle, SingleTileImageryProvider } from 'cesium';
import type { Viewer } from 'cesium';
import type { ScenarioId } from '../../project';
import { initialMorphologyOptions, loadMorphology, selectMorphologyLayer } from './data';
import type { MorphologyOptions } from './data';

export function createMorphologyLayer(viewer: Viewer, onError: (message: string | null) => void) {
  const loaded = new Map<string, ImageryLayer>();
  const pending = new Map<string, Promise<ImageryLayer>>();
  let options = initialMorphologyOptions;
  let scenario: ScenarioId = 'baseline';
  let generation = 0;
  let focusRequest: number | undefined;
  let disposed = false;

  function requestLayer(id: string, url: string, bounds: number[]) {
    const existing = pending.get(id);
    if (existing) {
      return existing;
    }

    const rectangle = Rectangle.fromDegrees(bounds[0]!, bounds[1]!, bounds[2]!, bounds[3]!);
    const request = SingleTileImageryProvider.fromUrl(url, { rectangle }).then((provider) => {
      const layer = new ImageryLayer(provider, { show: false });
      if (disposed) {
        layer.destroy();
        return layer;
      }

      viewer.imageryLayers.add(layer);
      loaded.set(id, layer);
      return layer;
    }).catch((error: unknown) => {
      pending.delete(id);
      throw error;
    });

    pending.set(id, request);
    return request;
  }

  async function update() {
    const request = ++generation;
    try {
      const data = await loadMorphology();
      if (disposed || request !== generation) {
        return;
      }

      const wanted = options.order.filter((id) => options.layers[id]?.enabled);
      const definitions = wanted.map((id) => ({ id, map: selectMorphologyLayer(data, id, scenario) }));
      const wantedIds = new Set(definitions.flatMap(({ map }) => map ? [map.id] : []));
      for (const [id, layer] of loaded) {
        layer.show = wantedIds.has(id);
      }

      await Promise.all(definitions.map(async ({ id, map }) => {
        if (!map) {
          return;
        }
        const layer = loaded.get(map.id) ?? await requestLayer(map.id, map.url, map.bounds);
        if (!disposed && request === generation) {
          layer.show = true;
          layer.alpha = options.layers[id]!.opacity;
        }
      }));
      if (disposed || request !== generation) {
        return;
      }

      // Bottom-to-top ordering is explicit and identical in both comparison panes.
      for (const { map } of definitions) {
        const layer = map && loaded.get(map.id);
        if (layer) {
          viewer.imageryLayers.raiseToTop(layer);
        }
      }

      const missing = definitions.filter(({ map }) => !map);
      onError(missing.length ? 'Some enabled indicators were not supplied for Current; their selections are retained for V1/V2.' : null);
      viewer.scene.requestRender();
    } catch (error) {
      if (!disposed && request === generation) {
        onError(error instanceof Error ? error.message : 'Morphology maps could not load');
      }
    }
  }

  return {
    setOptions(value: MorphologyOptions) {
      if (focusRequest === undefined) {
        focusRequest = value.focusRequest;
      }
      const focusChanged = focusRequest !== value.focusRequest;
      focusRequest = value.focusRequest;
      options = value;
      if (focusChanged) {
        const requested = value.focusRequest;
        void loadMorphology().then((data) => {
          if (disposed || focusRequest !== requested) {
            return;
          }
          const selected = value.order.find((id) => value.layers[id]?.enabled);
          const map = selected ? selectMorphologyLayer(data, selected, scenario) : undefined;
          const bounds = map?.bounds ?? data.layers[0]?.bounds;
          if (bounds) {
            viewer.camera.cancelFlight();
            viewer.camera.setView({ destination: Rectangle.fromDegrees(...bounds) });
            viewer.scene.requestRender();
          }
        }).catch((error: unknown) => {
          if (!disposed) {
            onError(error instanceof Error ? error.message : 'Analysis area unavailable');
          }
        });
      }
      void update();
    },
    setScenario(value: ScenarioId) {
      scenario = value;
      for (const layer of loaded.values()) {
        layer.show = false;
      }
      void update();
    },
    dispose() {
      disposed = true;
      generation++;
      for (const layer of loaded.values()) {
        viewer.imageryLayers.remove(layer, true);
      }
    },
  };
}
