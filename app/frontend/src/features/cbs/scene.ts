import {
  Cartesian3,
  Cartographic,
  ClassificationType,
  Color,
  ColorMaterialProperty,
  ConstantProperty,
  Entity,
  GeoJsonDataSource,
  Math as CesiumMath,
  Rectangle,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
} from 'cesium';
import type { Cartesian2, Viewer } from 'cesium';
import { cbsColour, cbsFeatureAt, cbsRange, initialCbsOptions, loadCbs } from './data';
import type { CbsData, CbsFeature, CbsOptions } from './data';

export function createCbsLayer(
  viewer: Viewer,
  onSelect: (id: string) => void,
  onError: (message: string | null) => void,
) {
  let options = initialCbsOptions;
  let source: GeoJsonDataSource | undefined;
  let data: CbsData | undefined;
  let disposed = false;
  let pending = false;
  let lastFocusRequest: number | undefined;

  function focusArea() {
    if (!data || lastFocusRequest === options.focusRequest) {
      return;
    }

    const [west, south, east, north] = data.bounds;
    const destination = Rectangle.fromDegrees(west - 0.002, south - 0.001, east + 0.002, north + 0.001);

    viewer.camera.cancelFlight();
    viewer.camera.setView({
      destination,
      orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 },
    });
    lastFocusRequest = options.focusRequest;
  }

  function update() {
    if (!source || !data || disposed) {
      return;
    }

    source.show = options.enabled;
    if (!options.enabled) {
      viewer.scene.requestRender();
      return;
    }

    const range = cbsRange(data, options.metric);
    const featuresByCode = new Map(data.neighbourhoods.features.map((feature) => [feature.id, feature]));

    for (const entity of source.entities.values) {
      const code = entity.properties?.buurtcode?.getValue();
      const selected = code === options.selected;

      if (entity.polyline) {
        const boundaryColour = Color.fromCssColorString(selected ? '#e8a735' : '#38536a');
        entity.polyline.material = new ColorMaterialProperty(boundaryColour);
        entity.polyline.width = new ConstantProperty(selected ? 4 : 1.5);
      }

      if (entity.polygon) {
        const value = featuresByCode.get(code)?.properties[options.metric];
        const fillColour = Color.fromCssColorString(cbsColour(value, range)).withAlpha(options.opacity);
        entity.polygon.material = new ColorMaterialProperty(fillColour);
        entity.polygon.outline = new ConstantProperty(false);
        entity.polygon.classificationType = new ConstantProperty(ClassificationType.TERRAIN);
      }
    }

    viewer.scene.requestRender();
  }

  function addBoundary(feature: CbsFeature, loaded: GeoJsonDataSource) {
    let polygons;
    if (feature.geometry.type === 'MultiPolygon') {
      polygons = feature.geometry.coordinates;
    } else {
      polygons = [feature.geometry.coordinates];
    }

    for (const [part, polygon] of polygons.entries()) {
      for (const [ringIndex, ring] of polygon.entries()) {
        const coordinates = ring.flatMap((point) => point.slice(0, 2));
        loaded.entities.add({
          id: `boundary-${feature.id}-${part}-${ringIndex}`,
          properties: { buurtcode: feature.id },
          polyline: {
            positions: Cartesian3.fromDegreesArray(coordinates),
            clampToGround: true,
            width: 1.5,
            material: Color.fromCssColorString('#38536a'),
            classificationType: ClassificationType.TERRAIN,
          },
        });
      }
    }
  }

  async function load() {
    pending = true;
    onError(null);

    try {
      const prepared = await loadCbs();
      if (disposed) {
        return;
      }

      const loaded = await GeoJsonDataSource.load(prepared.neighbourhoods, {
        clampToGround: true,
        stroke: Color.fromCssColorString('#38536a'),
        strokeWidth: 2,
      });
      if (disposed) {
        return;
      }

      loaded.show = false;
      for (const feature of prepared.neighbourhoods.features) {
        addBoundary(feature, loaded);
      }

      await viewer.dataSources.add(loaded);
      if (disposed) {
        if (!viewer.isDestroyed()) {
          viewer.dataSources.remove(loaded, true);
        }
        return;
      }

      data = prepared;
      source = loaded;
      update();
    } catch (cause) {
      if (!disposed) {
        const message = cause instanceof Error ? cause.message : 'CBS polygons could not load';
        onError(message);
      }
    } finally {
      pending = false;
    }
  }

  const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction((event: { position: Cartesian2 }) => {
    if (!options.enabled || !source || disposed) {
      return;
    }

    const currentSource = source;
    const picked = viewer.scene.drillPick(event.position).find((item) => {
      return item.id instanceof Entity && currentSource.entities.contains(item.id);
    });
    const code = picked?.id.properties?.buurtcode?.getValue();
    if (typeof code === 'string') {
      onSelect(code);
      return;
    }

    // Local site meshes can cover the classified globe, so also resolve the geographic footprint.
    let position: Cartesian3 | undefined;
    if (viewer.scene.pickPositionSupported) {
      position = viewer.scene.pickPosition(event.position);
    }
    if (!position) {
      const ray = viewer.camera.getPickRay(event.position);
      if (ray) {
        position = viewer.scene.globe.pick(ray, viewer.scene);
      }
    }
    if (!position || !data) {
      return;
    }

    const geographic = Cartographic.fromCartesian(position);
    const longitude = CesiumMath.toDegrees(geographic.longitude);
    const latitude = CesiumMath.toDegrees(geographic.latitude);
    const feature = cbsFeatureAt(data, longitude, latitude);
    if (feature) {
      onSelect(feature.id);
    }
  }, ScreenSpaceEventType.LEFT_CLICK);

  return {
    setOptions(value: CbsOptions) {
      if (lastFocusRequest === undefined) {
        // A newly opened Compare pane should inherit its linked camera, not replay an old focus action.
        lastFocusRequest = value.focusRequest;
      }

      const focusChanged = lastFocusRequest !== value.focusRequest;
      options = value;
      if (focusChanged) {
        if (data) {
          focusArea();
        } else {
          const requested = value.focusRequest;
          void loadCbs().then((prepared) => {
            if (!disposed && options.enabled && options.focusRequest === requested) {
              data = prepared;
              focusArea();
            }
          }).catch(() => {});
        }
      }
      if (value.enabled && !source && !pending) {
        void load();
      }

      update();
    },
    dispose() {
      disposed = true;
      handler.destroy();

      if (source) {
        viewer.dataSources.remove(source, true);
      }
    },
  };
}
