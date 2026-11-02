import { ImageryLayer, Rectangle, SingleTileImageryProvider } from 'cesium';
import type { Viewer } from 'cesium';
import type { ScenarioId } from '../../project';
import { initialMorphologyOptions, loadMorphology, selectMorphologyLayer } from './data';
import type { MorphologyOptions } from './data';

export function createMorphologyLayer(viewer: Viewer, onError: (message: string | null) => void) {
  let options = initialMorphologyOptions;
  let scenario: ScenarioId = 'baseline';
  let current: ImageryLayer | undefined;
  let currentId: string | undefined;
  let generation = 0;
  let focusRequest: number | undefined;
  let disposed = false;

  async function update() {
    const request = ++generation;
    if (current) {
      current.show = options.enabled;
      current.alpha = options.opacity;
    }
    if (!options.enabled) {
      viewer.scene.requestRender();
      return;
    }

    try {
      const data = await loadMorphology();
      if (disposed || request !== generation) {
        return;
      }

      const selected = selectMorphologyLayer(data, options.indicator, scenario);
      if (!selected) {
        if (current) {
          current.show = false;
        }
        onError('This indicator was not supplied for Current. Select V1 or V2.');
        viewer.scene.requestRender();
        return;
      }

      const rectangle = Rectangle.fromDegrees(...selected.bounds);
      if (selected.id !== currentId) {
        if (current) {
          current.show = false;
        }
        const provider = await SingleTileImageryProvider.fromUrl(selected.url, { rectangle });
        if (disposed || request !== generation) {
          return;
        }

        const replacement = new ImageryLayer(provider, { alpha: options.opacity });
        viewer.imageryLayers.add(replacement);
        if (current) {
          viewer.imageryLayers.remove(current, true);
        }
        current = replacement;
        currentId = selected.id;
      }

      current!.show = true;
      current!.alpha = options.opacity;
      if (focusRequest !== options.focusRequest) {
        viewer.camera.cancelFlight();
        viewer.camera.setView({ destination: rectangle });
        focusRequest = options.focusRequest;
      }
      onError(null);
      viewer.scene.requestRender();
    } catch (error) {
      if (!disposed && request === generation) {
        onError(error instanceof Error ? error.message : 'Morphology map could not load');
      }
    }
  }

  return {
    setOptions(value: MorphologyOptions) {
      if (focusRequest === undefined) {
        focusRequest = value.focusRequest;
      }
      const styleOnly = options.enabled === value.enabled && options.indicator === value.indicator
        && options.focusRequest === value.focusRequest;
      options = value;
      if (styleOnly) {
        if (current) {
          current.alpha = value.opacity;
        }
        viewer.scene.requestRender();
        return;
      }

      void update();
    },
    setScenario(value: ScenarioId) {
      scenario = value;
      if (current) {
        current.show = false;
      }
      void update();
    },
    dispose() {
      disposed = true;
      generation++;
      if (current) {
        viewer.imageryLayers.remove(current, true);
      }
    },
  };
}
