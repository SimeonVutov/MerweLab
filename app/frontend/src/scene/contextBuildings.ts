import {
  Cartesian3, Color, ColorGeometryInstanceAttribute, GeometryInstance,
  PerInstanceColorAppearance, PolygonGeometry, PolygonHierarchy, Primitive, PrimitiveCollection, Rectangle,
} from 'cesium';
import type { Viewer } from 'cesium';

interface Tile { url: string; bounds: [number, number, number, number] }
interface Footprint {
  id: string;
  properties: { bag_id: string; base_ellipsoid_m: number; roof_ellipsoid_m: number };
  geometry: { coordinates: number[][][] };
}

export function createContextBuildings(viewer: Viewer, onError: () => void) {
  const collection = viewer.scene.primitives.add(new PrimitiveCollection());
  const abort = new AbortController();
  const loaded = new Map<string, Primitive>();
  const pending = new Set<string>();
  const failed = new Set<string>();
  let tiles: Tile[] = [];
  let visible = new Set<string>();
  let enabled = true;
  let disposed = false;
  let active = 0;

  async function load(tile: Tile) {
    const response = await fetch(tile.url, { signal: abort.signal });
    if (!response.ok || !response.headers.get('content-type')?.includes('json')) throw new Error('Context tile unavailable');
    const data: { features: Footprint[] } = await response.json();
    if (!Array.isArray(data.features)) throw new Error('Invalid context tile');
    if (disposed) return;
    const instances = data.features.map((feature) => {
      if (!Number.isFinite(feature.properties?.base_ellipsoid_m) || !Number.isFinite(feature.properties?.roof_ellipsoid_m)
        || feature.properties.roof_ellipsoid_m <= feature.properties.base_ellipsoid_m
        || !feature.geometry?.coordinates?.length) throw new Error('Invalid context building');
      const rings = feature.geometry.coordinates.map((ring) => Cartesian3.fromDegreesArray(ring.flat()));
      return new GeometryInstance({
        id: { bagId: feature.properties.bag_id, source: '3DBAG context' },
        geometry: new PolygonGeometry({
          polygonHierarchy: new PolygonHierarchy(rings[0]!, rings.slice(1).map((ring) => new PolygonHierarchy(ring))),
          height: feature.properties.base_ellipsoid_m,
          extrudedHeight: feature.properties.roof_ellipsoid_m,
          vertexFormat: PerInstanceColorAppearance.VERTEX_FORMAT,
        }),
        attributes: { color: ColorGeometryInstanceAttribute.fromColor(Color.fromCssColorString('#b9beb9')) },
      });
    });
    const primitive = collection.add(new Primitive({
      geometryInstances: instances,
      appearance: new PerInstanceColorAppearance({ translucent: false, closed: true }),
      asynchronous: true,
      show: visible.has(tile.url),
    }));
    loaded.set(tile.url, primitive);
    viewer.scene.requestRender();
  }

  function pump() {
    if (disposed || !enabled) return;
    for (const tile of tiles) {
      if (active >= 4) break;
      if (!visible.has(tile.url) || loaded.has(tile.url) || pending.has(tile.url) || failed.has(tile.url)) continue;
      active++;
      pending.add(tile.url);
      void load(tile).catch((cause: unknown) => {
        if (disposed) return;
        failed.add(tile.url);
        console.error('Context building tile failed', cause);
        onError();
      }).finally(() => {
        active--;
        pending.delete(tile.url);
        pump();
      });
    }
  }

  function update() {
    if (disposed || !enabled) return;
    const view = viewer.camera.computeViewRectangle(viewer.scene.globe.ellipsoid);
    visible = new Set(tiles.filter((tile) => view && Rectangle.intersection(view, Rectangle.fromDegrees(...tile.bounds))).map((tile) => tile.url));
    for (const [url, primitive] of loaded) primitive.show = visible.has(url);
    pump();
    viewer.scene.requestRender();
  }

  const removeMove = viewer.camera.moveEnd.addEventListener(update);
  void fetch('/web/context/manifest.json', { signal: abort.signal }).then(async (response) => {
    if (!response.ok || !response.headers.get('content-type')?.includes('json')) throw new Error('Context manifest unavailable');
    const data: { version: number; tiles: Tile[] } = await response.json();
    if (data.version !== 1 || !Array.isArray(data.tiles) || !data.tiles.every((tile) =>
      /^\/web\/context\/[\w.-]+\.geojson$/.test(tile.url) && !tile.url.includes('..')
      && tile.bounds?.length === 4 && tile.bounds.every(Number.isFinite)
      && tile.bounds[0] < tile.bounds[2] && tile.bounds[1] < tile.bounds[3])) {
      throw new Error('Invalid context manifest');
    }
    if (disposed) return;
    tiles = data.tiles;
    update();
  }).catch((cause: unknown) => {
    if (disposed) return;
    console.error('Context buildings unavailable', cause);
    onError();
  });

  return {
    setVisible(value: boolean) { enabled = value; collection.show = value; update(); },
    dispose() {
      disposed = true;
      abort.abort();
      removeMove();
      viewer.scene.primitives.remove(collection);
    },
  };
}

export type ContextBuildings = ReturnType<typeof createContextBuildings>;
