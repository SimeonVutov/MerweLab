import {
  Axis,
  Cartesian2,
  Cartesian3,
  Color,
  ImageryLayer,
  Model,
  PointPrimitiveCollection,
  Rectangle,
  SingleTileImageryProvider,
  Transforms,
} from 'cesium';
import type { Viewer } from 'cesium';
import type { ViewMode } from '../../scene/camera';
import { initialEnvironmentOptions } from './types';
import type { EnvironmentInfo, EnvironmentManifest, EnvironmentOptions, TreeTile } from './types';

const TILE_DISTANCE = 3500;

function validAssetUrl(url: unknown): url is string {
  return typeof url === 'string' && /^\/web\/environment\/[\w.-]+$/.test(url) && !url.includes('..');
}

function validCoordinates(value: unknown, length: number): value is number[] {
  return Array.isArray(value) && value.length === length && value.every(Number.isFinite);
}

function validateManifest(manifest: EnvironmentManifest) {
  if (manifest.version !== 1 || !validAssetUrl(manifest.elevation?.url)
    || !validCoordinates(manifest.elevation?.bounds, 4)
    || !validAssetUrl(manifest.trees?.locations) || !Array.isArray(manifest.trees?.tiles)) {
    throw new Error('Unsupported environment manifest');
  }

  const [west, south, east, north] = manifest.elevation.bounds;
  if (west >= east || south >= north) {
    throw new Error('Invalid elevation coverage');
  }

  for (const tile of manifest.trees.tiles) {
    if (!validAssetUrl(tile.url) || !validCoordinates(tile.origin, 3)
      || !validCoordinates(tile.centre, 2) || !Number.isInteger(tile.count) || tile.count < 1) {
      throw new Error('Invalid tree tile');
    }
  }
}

export function createEnvironmentLayers(viewer: Viewer, onInfo: (info: EnvironmentInfo) => void) {
  const abort = new AbortController();
  const models = new Map<string, Model>();
  const pendingTiles = new Set<string>();
  const failures = new Set<string>();
  const markers = new PointPrimitiveCollection();
  viewer.scene.primitives.add(markers);
  markers.show = false;

  let options = initialEnvironmentOptions;
  let viewMode: ViewMode = '3d';
  let disposed = false;
  let manifest: EnvironmentManifest | undefined;
  let manifestRequest: Promise<void> | undefined;
  let elevation: ImageryLayer | undefined;
  let elevationPending = false;
  let markersLoaded = false;
  let markersPending = false;
  let error: string | null = null;

  function publish() {
    let treeStatus = 'Off';
    if (options.trees) {
      treeStatus = 'Loading';
      if (viewMode === '2d' && markersLoaded) {
        treeStatus = 'Locations loaded';
      } else if (viewMode === '3d' && manifest && pendingTiles.size === 0) {
        treeStatus = 'Loaded near view';
      }
    }

    let elevationStatus = 'Off';
    if (options.elevation) {
      elevationStatus = elevation ? 'Loaded' : 'Loading';
    }
    onInfo({ trees: treeStatus, elevation: elevationStatus, error });
  }

  async function readJson(url: string): Promise<unknown> {
    if (!validAssetUrl(url)) {
      throw new Error('Invalid environment asset URL');
    }

    const response = await fetch(url, { signal: abort.signal });
    if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
      throw new Error('Environment data is unavailable. Restart the frontend server after updating assets.');
    }
    return response.json();
  }

  function reportFailure(cause: unknown) {
    if (disposed) {
      return;
    }
    error = cause instanceof Error ? cause.message : 'Environment data could not load';
    publish();
  }

  async function loadTile(tile: TreeTile) {
    if (pendingTiles.has(tile.url) || models.has(tile.url) || failures.has(tile.url)) {
      return;
    }
    pendingTiles.add(tile.url);

    try {
      const position = Cartesian3.fromDegrees(...tile.origin);
      const model = await Model.fromGltfAsync({
        url: tile.url,
        modelMatrix: Transforms.eastNorthUpToFixedFrame(position),
        // Prepared coordinates are (east, up, -north), like the building models.
        upAxis: Axis.Y,
        forwardAxis: Axis.X,
        environmentMapOptions: { enabled: false },
        show: false,
      });
      if (disposed) {
        model.destroy();
        return;
      }

      model.imageBasedLighting.imageBasedLightingFactor = new Cartesian2(1, 0);
      viewer.scene.primitives.add(model);
      models.set(tile.url, model);
    } catch (cause) {
      failures.add(tile.url);
      reportFailure(cause);
    } finally {
      pendingTiles.delete(tile.url);
      if (!disposed) {
        updateTrees();
        publish();
      }
    }
  }

  async function loadMarkers() {
    if (!manifest || markersLoaded || markersPending) {
      return;
    }
    markersPending = true;

    try {
      const positions = await readJson(manifest.trees.locations);
      if (disposed) {
        return;
      }
      if (!Array.isArray(positions) || !positions.every((point) => validCoordinates(point, 3))) {
        throw new Error('Invalid tree locations');
      }

      for (const point of positions) {
        markers.add({
          position: Cartesian3.fromDegrees(point[0]!, point[1]!, point[2]!),
          color: Color.fromCssColorString('#57954b'),
          outlineColor: Color.fromCssColorString('#183f19'),
          outlineWidth: 1,
          pixelSize: 7,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        });
      }
      markersLoaded = true;
      viewer.scene.requestRender();
    } catch (cause) {
      reportFailure(cause);
    } finally {
      markersPending = false;
      if (!disposed) {
        publish();
      }
    }
  }

  function updateTrees() {
    if (disposed || !manifest) {
      return;
    }
    markers.show = options.trees && viewMode === '2d';
    if (markers.show) {
      void loadMarkers();
    }

    for (const tile of manifest.trees.tiles) {
      const centre = Cartesian3.fromDegrees(...tile.centre);
      const nearView = Cartesian3.distance(viewer.camera.positionWC, centre) < TILE_DISTANCE;
      const visible = options.trees && viewMode === '3d' && nearView;
      const model = models.get(tile.url);
      if (model) {
        model.show = visible;
      } else if (visible) {
        void loadTile(tile);
      }
    }
    viewer.scene.requestRender();
  }

  async function loadElevation() {
    if (!manifest || elevation || elevationPending) {
      return;
    }
    elevationPending = true;

    try {
      const provider = await SingleTileImageryProvider.fromUrl(manifest.elevation.url, {
        rectangle: Rectangle.fromDegrees(...manifest.elevation.bounds),
      });
      const layer = new ImageryLayer(provider, { show: false });
      if (disposed) {
        layer.destroy();
        return;
      }

      // Base context colours stay below analytical overlays, even when loaded later.
      viewer.imageryLayers.add(layer, Math.min(2, viewer.imageryLayers.length));
      elevation = layer;
      layer.show = options.elevation;
      layer.alpha = options.elevationOpacity;
      viewer.scene.requestRender();
    } catch (cause) {
      reportFailure(cause);
    } finally {
      elevationPending = false;
      if (!disposed) {
        publish();
      }
    }
  }

  async function ensureManifest() {
    if (!manifestRequest) {
      manifestRequest = readJson('/web/environment/manifest.json').then((data) => {
        const definition = data as EnvironmentManifest;
        validateManifest(definition);
        manifest = definition;
      }).catch((cause: unknown) => {
        manifestRequest = undefined;
        throw cause;
      });
    }
    await manifestRequest;
  }

  async function update() {
    if (elevation) {
      elevation.show = options.elevation;
      elevation.alpha = options.elevationOpacity;
    }
    markers.show = options.trees && viewMode === '2d';
    for (const model of models.values()) {
      model.show = false;
    }

    if (!options.trees && !options.elevation) {
      publish();
      viewer.scene.requestRender();
      return;
    }

    try {
      await ensureManifest();
      if (disposed) {
        return;
      }
      updateTrees();
      if (options.elevation) {
        void loadElevation();
      }
      publish();
    } catch (cause) {
      reportFailure(cause);
    }
  }

  const removeCameraListener = viewer.camera.moveEnd.addEventListener(updateTrees);

  return {
    setOptions(value: EnvironmentOptions, mode: ViewMode) {
      options = value;
      viewMode = mode;
      void update();
    },
    dispose() {
      disposed = true;
      abort.abort();
      removeCameraListener();
      for (const model of models.values()) {
        viewer.scene.primitives.remove(model);
      }
      models.clear();
      viewer.scene.primitives.remove(markers);
      if (elevation) {
        viewer.imageryLayers.remove(elevation, true);
      }
    },
  };
}
