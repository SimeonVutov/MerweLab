import {
  Cartesian3, Color, ColorMaterialProperty, ConstantProperty, Entity,
  PolylineDashMaterialProperty, Rectangle, ScreenSpaceEventHandler, ScreenSpaceEventType,
} from 'cesium';
import type { Cartesian2, Viewer } from 'cesium';
import type { ScenarioId } from '../../project';
import { loadNetworkCollection, loadNetworkManifest } from './data';
import { networkColours, networkFeatureVisible, networkPathColour } from './appearance';
import { hasNetworkLayers, initialNetworkInfo, initialNetworkOptions, isNetworkPath, selectedNetworkVariant } from './types';
import type { NetworkCollection, NetworkFeature, NetworkInfo, NetworkManifest, NetworkOptions, NetworkPane } from './types';

interface RenderedNetwork {
  key: string;
  data: NetworkCollection;
  entities: Map<string, Entity>;
}

function createFeatureEntity(viewer: Viewer, feature: NetworkFeature, key: string) {
  const common = { id: `network:${key}:${feature.id}`, properties: { networkKey: key, networkFeatureId: feature.id } };
  if (isNetworkPath(feature)) {
    return viewer.entities.add({
      ...common,
      polyline: {
        positions: Cartesian3.fromDegreesArrayHeights(feature.geometry.coordinates.flat()),
        width: 3,
        clampToGround: false,
      },
    });
  }

  const [longitude, latitude, height] = feature.geometry.coordinates;
  return viewer.entities.add({
    ...common,
    position: Cartesian3.fromDegrees(longitude!, latitude!, height!),
    point: {
      pixelSize: feature.properties.layer === 'garage_ramp' ? 13 : 8,
      outlineWidth: 1.5,
      outlineColor: Color.fromCssColorString('#f1f1e8'),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  });
}

function styleFeature(entity: Entity, feature: NetworkFeature, options: NetworkOptions, data: NetworkManifest, selected: boolean) {
  entity.show = networkFeatureVisible(feature, options);
  let colour = networkColours.ramp as string;
  if (isNetworkPath(feature)) {
    colour = networkPathColour(feature, options.colour, data);
  } else if (feature.properties.layer === 'entrance') {
    colour = networkColours.entrance;
  }
  if (selected) colour = networkColours.selected;

  const displayColour = Color.fromCssColorString(colour).withAlpha(options.opacity);
  if (entity.polyline && isNetworkPath(feature)) {
    entity.polyline.width = new ConstantProperty(selected ? 6 : 3);
    entity.polyline.material = feature.properties.built
      ? new ColorMaterialProperty(displayColour)
      : new PolylineDashMaterialProperty({ color: displayColour, dashLength: 12 });
  }
  if (entity.point) {
    entity.point.color = new ConstantProperty(displayColour);
    entity.point.outlineColor = new ConstantProperty(Color.fromCssColorString('#f1f1e8').withAlpha(options.opacity));
  }
}

export function createNetworkLayer(viewer: Viewer, onInfo: (info: NetworkInfo) => void) {
  const loaded = new Map<string, RenderedNetwork>();
  const handler = new ScreenSpaceEventHandler(viewer.canvas);
  let options = initialNetworkOptions;
  let scenario: ScenarioId = 'baseline';
  let pane: NetworkPane = 'left';
  let manifest: NetworkManifest | undefined;
  let current: RenderedNetwork | undefined;
  let selectedId: string | null = null;
  let info = initialNetworkInfo;
  let generation = 0;
  let focusRequest = 0;
  let disposed = false;

  function publish(changes: Partial<NetworkInfo>) {
    if (disposed) return;

    info = { ...info, ...changes };
    onInfo(info);
  }

  function hideNetworks() {
    for (const network of loaded.values()) {
      for (const entity of network.entities.values()) entity.show = false;
    }
  }

  function applyStyle() {
    if (!current || !manifest || disposed) return;

    const selected = current.data.features.find((feature) => feature.id === selectedId);
    if (selected && !networkFeatureVisible(selected, options)) {
      selectedId = null;
      publish({ selected: null });
    }

    for (const feature of current.data.features) {
      styleFeature(current.entities.get(feature.id)!, feature, options, manifest, feature.id === selectedId);
    }
    viewer.scene.requestRender();
  }

  async function update() {
    const request = ++generation;
    const variant = selectedNetworkVariant(options, pane);
    const key = `${scenario}/${variant}`;
    hideNetworks();
    viewer.scene.requestRender();

    if (!hasNetworkLayers(options)) {
      publish({ status: 'Off', selected: null, error: null });
      return;
    }
    if (scenario === 'baseline') {
      current = undefined;
      publish({ status: 'Unavailable', selected: null, error: null });
      return;
    }

    try {
      publish({ status: 'Loading', error: null });
      const data = await loadNetworkManifest();
      if (disposed || request !== generation) return;

      const entry = data.scenarios[scenario]?.[variant];
      if (!entry) throw new Error('Network alternative is unavailable');

      let network = loaded.get(key);
      if (!network) {
        const collection = await loadNetworkCollection(entry.url);
        if (disposed || request !== generation) return;

        const entities = new Map(collection.features.map((feature) => [feature.id, createFeatureEntity(viewer, feature, key)]));
        network = { key, data: collection, entities };
        loaded.set(key, network);
      }
      if (disposed || request !== generation) return;

      if (current?.key !== key) selectedId = null;
      current = network;
      manifest = data;
      applyStyle();
      const selected = network.data.features.find((feature) => feature.id === selectedId) ?? null;
      publish({ status: 'Loaded', selected, error: null });
    } catch (error) {
      if (!disposed && request === generation) {
        publish({ status: 'Error', selected: null, error: error instanceof Error ? error.message : 'Network could not load' });
      }
    }
  }

  handler.setInputAction(({ position }: { position: Cartesian2 }) => {
    if (!hasNetworkLayers(options) || !current || info.status !== 'Loaded') return;

    const picked = viewer.scene.drillPick(position);
    const entity = picked.map((item) => item.id).find((item) => item instanceof Entity
      && item.properties?.networkKey?.getValue() === current!.key);
    selectedId = entity?.properties?.networkFeatureId?.getValue() ?? null;
    const selected = current.data.features.find((feature) => feature.id === selectedId) ?? null;
    publish({ selected });
    applyStyle();
  }, ScreenSpaceEventType.LEFT_CLICK);

  return {
    setScenario(value: ScenarioId) {
      scenario = value;
      selectedId = null;
      publish({ selected: null });
      void update();
    },
    setOptions(value: NetworkOptions, side: NetworkPane) {
      const shouldFocus = focusRequest !== value.focusRequest;
      options = value;
      pane = side;
      focusRequest = value.focusRequest;
      void update();

      // All other controls preserve the camera. Use the common bounds here so
      // the two comparison panes focus on the same area.
      if (shouldFocus && hasNetworkLayers(value)) {
        void loadNetworkManifest().then((data) => {
          if (disposed || focusRequest !== value.focusRequest) return;

          const [west, south, east, north] = data.bounds;
          viewer.camera.cancelFlight();
          viewer.camera.setView({ destination: Rectangle.fromDegrees(west - 0.0005, south - 0.0003, east + 0.0005, north + 0.0003) });
          viewer.scene.requestRender();
        }).catch((error: unknown) => {
          if (!disposed) publish({ error: error instanceof Error ? error.message : 'Network area unavailable' });
        });
      }
    },
    dispose() {
      disposed = true;
      generation++;
      handler.destroy();
      for (const network of loaded.values()) {
        for (const entity of network.entities.values()) viewer.entities.remove(entity);
      }
    },
  };
}
