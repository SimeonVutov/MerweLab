import {
  ArcType, BoundingSphere, Cartesian3, Cartographic, Color, ComponentDatatype, Geometry, GeometryAttribute,
  GeometryAttributes, GeometryInstance, Material, MaterialAppearance, Matrix4, PolylineCollection, PolylineColorAppearance,
  PolylineGeometry, Primitive, PrimitiveCollection, PrimitiveType, ScreenSpaceEventHandler,
  ScreenSpaceEventType, Transforms, Math as CesiumMath,
} from 'cesium';
import type { Cartesian2, Viewer } from 'cesium';
import type { ScenarioId } from '../../project';
import { initialWindInfo, initialWindOptions } from './types';
import type { WindInfo, WindLocation, WindMetric, WindMetricInfo, WindOptions, WindOverlay } from './types';

interface CaseData {
  width: number;
  height: number;
  bounds: [number, number, number, number];
  iteration: number;
  mesh: { positions: string; st: string; indices: string; vertexCount: number; indexCount: number };
  metrics: Record<WindMetric, WindMetricInfo>;
  overlays: Record<WindOverlay, string>;
  quality: { speed_above_100_m_s: number };
}
interface Manifest { version: number; originEcef: number[]; scenarios: Record<ScenarioId, CaseData> }
interface Line { points: number[][]; speed: number[] }
interface Surface { primitive: Primitive; material: Material; values: Float32Array; info: WindMetricInfo; data: CaseData }
interface Mesh { positions: Float64Array; st: Float32Array; indices: Uint32Array }

export function createWindLayer(viewer: Viewer, onInfo: (info: WindInfo) => void, onProbe?: (point: WindLocation) => void) {
  const collection = viewer.scene.primitives.add(new PrimitiveCollection());
  const abort = new AbortController();
  const maps = new Map<string, Promise<Surface>>();
  const meshes = new Map<ScenarioId, Promise<Mesh>>();
  const overlays = new Map<string, Promise<Primitive | PolylineCollection>>();
  const rendered = new Set<Primitive | PolylineCollection>();
  let manifestPromise: Promise<Manifest> | undefined;
  let options: WindOptions = initialWindOptions;
  let scenario: ScenarioId = 'baseline';
  let disposed = false;
  let generation = 0;
  let current: Surface | null = null;
  let info: WindInfo = initialWindInfo;
  let probeLocation: WindLocation | null = null;

  function publish(update: Partial<WindInfo>) {
    if (disposed) return;
    info = { ...info, ...update };
    onInfo(info);
  }

  async function fetchData(url: string) {
    if (!/^\/web\/wind\/[\w/.-]+$/.test(url) || url.includes('..')) throw new Error('Invalid wind asset path');
    const response = await fetch(url, { signal: abort.signal });
    if (!response.ok) throw new Error(`Wind asset ${url} unavailable (HTTP ${response.status})`);
    if (response.headers.get('content-type')?.includes('text/html')) {
      throw new Error(`Wind asset ${url} is missing. Generate the browser assets with scripts/web/prepare_wind.py.`);
    }
    if (url.endsWith('.gz') && !response.headers.get('content-encoding')?.includes('gzip')) {
      if (!response.body) throw new Error(`Empty wind asset ${url}`);
      return new Response(response.body.pipeThrough(new DecompressionStream('gzip')));
    }
    return response;
  }

  function manifest() {
    if (!manifestPromise) {
      manifestPromise = fetchData('/web/wind/manifest.json').then(async (response) => {
        const data: Manifest = await response.json();
        if (data.version !== 1 || data.originEcef?.length !== 3 || !data.originEcef.every(Number.isFinite)
          || !['baseline', 'scenario_a', 'scenario_b'].every((key) => key in data.scenarios)) throw new Error('Invalid wind manifest');
        return data;
      }).catch((cause: unknown) => { manifestPromise = undefined; throw cause; });
    }
    return manifestPromise;
  }

  function loadMesh(selected: ScenarioId, data: CaseData) {
    let request = meshes.get(selected);
    if (!request) {
      request = Promise.all([data.mesh.positions, data.mesh.st, data.mesh.indices].map(async (url) => (await fetchData(url)).arrayBuffer())).then(([positions, st, indices]) => {
        if (positions!.byteLength !== data.mesh.vertexCount * 12 || st!.byteLength !== data.mesh.vertexCount * 8 || indices!.byteLength !== data.mesh.indexCount * 4) throw new Error('Incomplete wind surface');
        return { positions: Float64Array.from(new Float32Array(positions!)), st: new Float32Array(st!), indices: new Uint32Array(indices!) };
      }).catch((cause: unknown) => { meshes.delete(selected); throw cause; });
      meshes.set(selected, request);
    }
    return request;
  }

  function loadMap(selected: ScenarioId, metric: WindMetric): Promise<Surface> {
    const key = `${selected}/${metric}`;
    const cached = maps.get(key);
    if (cached) return cached;
    const request = manifest().then(async (all) => {
      const data = all.scenarios[selected];
      const field = data.metrics[metric];
      const image = new Image();
      image.src = field.image;
      const [mesh, buffer] = await Promise.all([loadMesh(selected, data), fetchData(field.values).then((response) => response.arrayBuffer()), image.decode()]);
      if (disposed) throw new Error('Wind layer disposed');
      if (buffer.byteLength !== data.width * data.height * 4) throw new Error('Incomplete wind values');
      const normals = new Float32Array(data.mesh.vertexCount * 3);
      for (let index = 2; index < normals.length; index += 3) normals[index] = 1;
      const attributes = new GeometryAttributes();
      attributes.position = new GeometryAttribute({ componentDatatype: ComponentDatatype.DOUBLE, componentsPerAttribute: 3, values: mesh.positions.slice() });
      attributes.normal = new GeometryAttribute({ componentDatatype: ComponentDatatype.FLOAT, componentsPerAttribute: 3, values: normals });
      attributes.st = new GeometryAttribute({ componentDatatype: ComponentDatatype.FLOAT, componentsPerAttribute: 2, values: mesh.st.slice() });
      const geometry = new Geometry({
        attributes,
        indices: mesh.indices.slice(),
        primitiveType: PrimitiveType.TRIANGLES,
        boundingSphere: BoundingSphere.fromVertices(mesh.positions),
      });
      const material = new Material({ fabric: { type: 'Image', uniforms: { image, color: Color.WHITE.withAlpha(options.opacity) } }, translucent: true });
      const primitive = collection.add(new Primitive({
        geometryInstances: new GeometryInstance({ geometry, id: 'wind-surface' }),
        modelMatrix: Transforms.eastNorthUpToFixedFrame(Cartesian3.fromArray(all.originEcef)),
        appearance: new MaterialAppearance({ material, flat: true, translucent: true, closed: false }),
        asynchronous: false,
        show: false,
      }));
      rendered.add(primitive);
      return { primitive, material, values: new Float32Array(buffer), info: field, data };
    }).catch((cause: unknown) => { maps.delete(key); throw cause; });
    maps.set(key, request);
    return request;
  }

  function loadOverlay(selected: ScenarioId, kind: WindOverlay) {
    const key = `${selected}/${kind}`;
    const cached = overlays.get(key);
    if (cached) return cached;
    const request = manifest().then(async (all) => {
      const data = all.scenarios[selected];
      const lines: { lines: Line[] } = await (await fetchData(data.overlays[kind])).json();
      if (disposed) throw new Error('Wind layer disposed');
      const matrix = Transforms.eastNorthUpToFixedFrame(Cartesian3.fromArray(all.originEcef));
      const toWorld = (point: number[]) => Matrix4.multiplyByPoint(matrix, Cartesian3.fromArray(point), new Cartesian3());
      let primitive: Primitive | PolylineCollection;
      if (kind === 'arrows') {
        const arrows = new PolylineCollection();
        const material = Material.fromType('PolylineArrow', { color: Color.fromCssColorString('#172632') });
        for (const line of lines.lines) {
          const positions = line.points.map(toWorld);
          if (positions.length < 2 || Cartesian3.distance(positions[0]!, positions[1]!) < 0.01) continue;
          arrows.add({ positions, width: 4, material });
        }
        primitive = arrows;
      } else {
        const palette = data.metrics.speed.colours;
        const [low, high] = data.metrics.speed.range;
        const geometries = lines.lines.filter((line) => line.points.length >= 2).map((line) => new GeometryInstance({
          id: `wind-${kind}`,
          geometry: new PolylineGeometry({
            positions: line.points.map(toWorld), width: kind === 'streamlines_3d' ? 2.5 : 1.5,
            colors: line.speed.map((speed) => Color.fromCssColorString(palette[Math.round(Math.min(1, Math.max(0, (speed - low) / (high - low))) * 255)]!)),
            colorsPerVertex: true, arcType: ArcType.NONE, vertexFormat: PolylineColorAppearance.VERTEX_FORMAT,
          }),
        }));
        primitive = new Primitive({ geometryInstances: geometries, appearance: new PolylineColorAppearance({ translucent: false }), asynchronous: true });
      }
      primitive.show = false;
      collection.add(primitive);
      rendered.add(primitive);
      return primitive;
    }).catch((cause: unknown) => { overlays.delete(key); throw cause; });
    overlays.set(key, request);
    return request;
  }

  async function refresh() {
    const request = ++generation;
    current = null;
    rendered.forEach((primitive) => { primitive.show = false; });
    const enabled = options.metric || options.arrows || options.streamlines_2d || options.streamlines_3d;
    publish({ status: enabled ? 'Loading' : 'Off', metric: null, flowLegend: null, sample: null, error: null, flaggedSamples: 0 });
    viewer.scene.requestRender();
    if (!enabled) return;
    const selected = scenario;
    const wanted = { ...options };
    try {
      const jobs: Promise<void>[] = [];
      if (wanted.metric) jobs.push(loadMap(selected, wanted.metric).then((surface) => {
        if (disposed || generation !== request) return;
        current = surface;
        surface.material.uniforms.color = Color.WHITE.withAlpha(wanted.opacity);
        surface.primitive.show = true;
        publish({ metric: surface.info });
        if (probeLocation) sampleAt(probeLocation);
        viewer.scene.requestRender();
      }));
      for (const kind of ['arrows', 'streamlines_2d', 'streamlines_3d'] as const) {
        if (wanted[kind]) jobs.push(loadOverlay(selected, kind).then((primitive) => {
          if (disposed || generation !== request) return;
          primitive.show = true;
          viewer.scene.requestRender();
        }));
      }
      const results = await Promise.allSettled(jobs);
      if (disposed || generation !== request) return;
      const failure = results.find((result) => result.status === 'rejected');
      const all = await manifest();
      if (disposed || generation !== request) return;
      publish({ status: failure ? 'Unavailable' : 'Loaded', error: failure?.status === 'rejected' && failure.reason instanceof Error ? failure.reason.message : failure ? 'Some wind results could not load.' : null,
        flowLegend: wanted.streamlines_2d || wanted.streamlines_3d ? all.scenarios[selected].metrics.speed : null,
        flaggedSamples: all.scenarios[selected].quality.speed_above_100_m_s });
      if (failure?.status === 'rejected') console.error('Wind results failed', failure.reason);
    } catch (cause) {
      if (disposed || generation !== request) return;
      console.error('Wind results failed', cause);
      publish({ status: 'Unavailable', error: cause instanceof Error ? cause.message : 'Wind results could not load.' });
    }
  }

  const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
  const removeUpdate = viewer.scene.postUpdate.addEventListener(() => {
    if ([...rendered].some((primitive) => primitive.show && primitive instanceof Primitive && !primitive.ready)) viewer.scene.requestRender();
  });
  function sampleAt(point: WindLocation) {
    if (!current || disposed) return;
    const [west, south, east, north] = current.data.bounds;
    const lon = point.longitude, lat = point.latitude;
    let value: number | null = null;
    if (lon >= west && lon < east && lat > south && lat <= north) {
      const col = Math.floor((lon - west) / (east - west) * current.data.width);
      const row = Math.floor((north - lat) / (north - south) * current.data.height);
      const sample = current.values[row * current.data.width + col];
      if (sample !== undefined && Number.isFinite(sample) && sample !== -9999) value = sample;
    }
    publish({ sample: { value, outsideRange: value !== null && (value < current.info.range[0] || value > current.info.range[1]), flagged: options.metric === 'speed' && value !== null && value > 100 } });
  }

  handler.setInputAction((event: { position: Cartesian2 }) => {
    if (!current || disposed) return;
    let position: Cartesian3 | undefined;
    if (viewer.scene.pickPositionSupported) position = viewer.scene.pickPosition(event.position);
    if (!position) {
      const ray = viewer.camera.getPickRay(event.position);
      if (ray) position = viewer.scene.globe.pick(ray, viewer.scene);
    }
    if (!position) return;
    const point = Cartographic.fromCartesian(position);
    probeLocation = { longitude: CesiumMath.toDegrees(point.longitude), latitude: CesiumMath.toDegrees(point.latitude) };
    sampleAt(probeLocation);
    onProbe?.(probeLocation);
  }, ScreenSpaceEventType.LEFT_CLICK);

  return {
    setProbe(point: WindLocation | null) { probeLocation = point; if (point) sampleAt(point); else publish({ sample: null }); },
    setScenario(value: ScenarioId) { scenario = value; void refresh(); },
    setOptions(value: WindOptions) {
      const styleOnly = options.metric === value.metric && options.arrows === value.arrows
        && options.streamlines_2d === value.streamlines_2d && options.streamlines_3d === value.streamlines_3d;
      options = value;
      if (styleOnly && current) {
        current.material.uniforms.color = Color.WHITE.withAlpha(value.opacity);
        viewer.scene.requestRender();
      } else void refresh();
    },
    dispose() { disposed = true; generation++; abort.abort(); removeUpdate(); handler.destroy(); viewer.scene.primitives.remove(collection); },
  };
}

export type WindLayer = ReturnType<typeof createWindLayer>;
