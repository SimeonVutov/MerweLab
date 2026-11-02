import {
  BoundingSphere,
  Cartesian3,
  Cartographic,
  ComponentDatatype,
  Geometry,
  GeometryAttribute,
  GeometryAttributes,
  GeometryInstance,
  Material,
  MaterialAppearance,
  Math as CesiumMath,
  Primitive,
  PrimitiveCollection,
  PrimitiveType,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  TextureMagnificationFilter,
  TextureMinificationFilter,
  Transforms,
} from 'cesium';
import type { Cartesian2, Viewer } from 'cesium';
import {
  fetchNoiseAsset,
  loadNoiseManifest,
  nearestNoiseReceiver,
  noiseCodeAt,
  validateNoiseReceivers,
} from './data';
import type { NoiseManifest, NoiseReceiver, NoiseScenario } from './data';
import { initialNoiseInfo, initialNoiseOptions } from './types';
import type { NoiseClass, NoiseInfo, NoiseLocation, NoiseOptions, NoisePeriod, NoiseSample } from './types';
import type { ScenarioId } from '../../project';

interface NoiseMap {
  image: HTMLImageElement;
  codes: Uint8Array;
  data: NoiseScenario;
}

interface NoiseMesh {
  positions: Float64Array;
  st: Float32Array;
  indices: Uint32Array;
}

function materialSource(classes: NoiseClass[]) {
  const colours = classes.map((band) => {
    const rgb = [1, 3, 5].map((offset) => parseInt(band.colour.slice(offset, offset + 2), 16) / 255);
    return `if (code == ${band.code}.0) return vec3(${rgb.map((value) => value.toFixed(8)).join(', ')});`;
  }).join('\n');

  return `
    vec3 noiseColour(float code) {
      ${colours}
      return vec3(0.0);
    }

    czm_material czm_getMaterial(czm_materialInput materialInput) {
      czm_material material = czm_getDefaultMaterial(materialInput);
      float code = floor(texture(image, materialInput.st).r * 255.0 + 0.5);
      material.diffuse = noiseColour(code);
      material.alpha = 0.0;
      if (code >= minimumCode && code >= 1.0) {
        material.alpha = opacity;
      }
      return material;
    }
  `;
}

export function createNoiseLayer(
  viewer: Viewer,
  onInfo: (info: NoiseInfo) => void,
  onProbe: (point: NoiseLocation) => void,
) {
  const collection = viewer.scene.primitives.add(new PrimitiveCollection());
  const abort = new AbortController();
  const maps = new Map<string, Promise<NoiseMap>>();
  const receivers = new Map<ScenarioId, Promise<NoiseReceiver[]>>();
  let meshRequest: Promise<NoiseMesh> | undefined;
  let surface: { primitive: Primitive; material: Material } | undefined;
  let manifest: NoiseManifest | undefined;
  let current: NoiseMap | undefined;
  let options: NoiseOptions = initialNoiseOptions;
  let scenario: ScenarioId = 'baseline';
  let info: NoiseInfo = initialNoiseInfo;
  let probe: NoiseLocation | null = null;
  let generation = 0;
  let sampleGeneration = 0;
  let disposed = false;

  function publish(update: Partial<NoiseInfo>) {
    if (disposed) {
      return;
    }

    info = { ...info, ...update };
    onInfo(info);
  }

  function loadMap(selected: ScenarioId, period: NoisePeriod, data: NoiseScenario) {
    const key = `${selected}/${period}`;
    const cached = maps.get(key);
    if (cached) {
      return cached;
    }

    const request = (async () => {
      const response = await fetchNoiseAsset(data.maps[period].image, abort.signal);
      const url = URL.createObjectURL(await response.blob());
      const image = new Image();
      try {
        image.src = url;
        await image.decode();
      } finally {
        URL.revokeObjectURL(url);
      }

      if (disposed) {
        throw new Error('Noise layer disposed');
      }
      if (image.naturalWidth !== data.width || image.naturalHeight !== data.height) {
        throw new Error('Incomplete noise map image');
      }

      const canvas = document.createElement('canvas');
      canvas.width = data.width;
      canvas.height = data.height;
      const context = canvas.getContext('2d', { willReadFrequently: true });
      if (!context) {
        throw new Error('Noise map decoding is unavailable');
      }

      context.drawImage(image, 0, 0);
      const pixels = context.getImageData(0, 0, data.width, data.height).data;
      const codes = new Uint8Array(data.width * data.height);
      for (let index = 0; index < codes.length; index++) {
        if (pixels[index * 4 + 3] !== 0) {
          codes[index] = pixels[index * 4]!;
        }
        if (codes[index]! > 11) {
          throw new Error('Invalid noise class code in image');
        }
      }

      return { image, codes, data };
    })().catch((cause: unknown) => {
      maps.delete(key);
      throw cause;
    });

    maps.set(key, request);
    return request;
  }

  function loadMesh(data: NoiseManifest) {
    if (!meshRequest) {
      const urls = [data.mesh.positions, data.mesh.st, data.mesh.indices];
      meshRequest = Promise.all(urls.map(async (url) => {
        return (await fetchNoiseAsset(url, abort.signal)).arrayBuffer();
      })).then(([positions, st, indices]) => {
        if (positions!.byteLength !== data.mesh.vertexCount * 12
          || st!.byteLength !== data.mesh.vertexCount * 8
          || indices!.byteLength !== data.mesh.indexCount * 4) {
          throw new Error('Incomplete noise display mesh');
        }

        return {
          positions: Float64Array.from(new Float32Array(positions!)),
          st: new Float32Array(st!),
          indices: new Uint32Array(indices!),
        };
      }).catch((cause: unknown) => {
        meshRequest = undefined;
        throw cause;
      });
    }

    return meshRequest;
  }

  function createSurface(data: NoiseManifest, mesh: NoiseMesh, image: HTMLImageElement) {
    const attributes = new GeometryAttributes();
    attributes.position = new GeometryAttribute({
      componentDatatype: ComponentDatatype.DOUBLE,
      componentsPerAttribute: 3,
      values: mesh.positions,
    });
    attributes.st = new GeometryAttribute({
      componentDatatype: ComponentDatatype.FLOAT,
      componentsPerAttribute: 2,
      values: mesh.st,
    });
    const normals = new Float32Array(data.mesh.vertexCount * 3);
    for (let index = 2; index < normals.length; index += 3) {
      normals[index] = 1;
    }
    attributes.normal = new GeometryAttribute({
      componentDatatype: ComponentDatatype.FLOAT,
      componentsPerAttribute: 3,
      values: normals,
    });

    const geometry = new Geometry({
      attributes,
      indices: mesh.indices,
      primitiveType: PrimitiveType.TRIANGLES,
      boundingSphere: BoundingSphere.fromVertices(mesh.positions),
    });
    const material = new Material({
      fabric: {
        type: 'NoiseBands',
        uniforms: { image, minimumCode: 1, opacity: options.opacity },
        source: materialSource(data.classes),
      },
      minificationFilter: TextureMinificationFilter.NEAREST,
      magnificationFilter: TextureMagnificationFilter.NEAREST,
      translucent: true,
    });
    const primitive = new Primitive({
      geometryInstances: new GeometryInstance({ geometry, id: 'noise-map' }),
      modelMatrix: Transforms.eastNorthUpToFixedFrame(Cartesian3.fromArray(data.mesh.originEcef)),
      appearance: new MaterialAppearance({ material, flat: true, translucent: true, closed: false }),
      asynchronous: false,
      show: false,
    });

    collection.add(primitive);
    return { primitive, material };
  }

  function applyStyle() {
    if (!surface) {
      return;
    }

    let minimumCode = 1;
    if (options.thresholdEnabled) {
      minimumCode = (options.threshold - 35) / 5 + 2;
    }

    surface.material.uniforms.minimumCode = minimumCode;
    surface.material.uniforms.opacity = options.opacity;
    viewer.scene.requestRender();
  }

  function loadReceivers(selected: ScenarioId, data: NoiseScenario) {
    // Never inspect, fetch or infer V1 receiver values, even if a URL is accidentally supplied.
    if (selected === 'scenario_a' || !data.receivers) {
      return Promise.resolve([]);
    }

    const cached = receivers.get(selected);
    if (cached) {
      return cached;
    }

    const definition = data.receivers;
    const request = fetchNoiseAsset(definition.url, abort.signal).then(async (response) => {
      const result: { receivers: NoiseReceiver[] } = await response.json();
      validateNoiseReceivers(result.receivers, definition.count);
      return result.receivers;
    }).catch((cause: unknown) => {
      receivers.delete(selected);
      throw cause;
    });

    receivers.set(selected, request);
    return request;
  }

  function sampleAt(point: NoiseLocation) {
    if (!current || !manifest || disposed) {
      return;
    }

    const request = ++sampleGeneration;
    const selected = scenario;
    const period = options.period;
    const code = noiseCodeAt(current.codes, current.data, point);
    const band = manifest.classes.find((candidate) => candidate.code === code) ?? null;
    const sample: NoiseSample = { band, receiver: null, receiverStatus: 'Loading' };
    if (selected === 'scenario_a') {
      sample.receiverStatus = 'Unavailable for V1';
      publish({ sample });
      return;
    }

    publish({ sample });
    void loadReceivers(selected, current.data).then((points) => {
      if (disposed || request !== sampleGeneration) {
        return;
      }

      const receiver = nearestNoiseReceiver(points, point, period);
      publish({ sample: { ...sample, receiver, receiverStatus: 'Loaded' } });
    }).catch(() => {
      if (!disposed && request === sampleGeneration) {
        publish({ sample: { ...sample, receiverStatus: 'Unavailable' } });
      }
    });
  }

  async function refresh() {
    const request = ++generation;
    sampleGeneration++;
    current = undefined;
    if (surface) {
      surface.primitive.show = false;
    }

    publish({ status: options.enabled ? 'Loading' : 'Off', error: null, sample: null });
    viewer.scene.requestRender();
    if (!options.enabled) {
      return;
    }

    const selected = scenario;
    const period = options.period;
    try {
      const data = await loadNoiseManifest();
      const [map, mesh] = await Promise.all([
        loadMap(selected, period, data.scenarios[selected]),
        loadMesh(data),
      ]);
      if (disposed || request !== generation) {
        return;
      }

      manifest = data;
      current = map;
      if (!surface) {
        surface = createSurface(data, mesh, map.image);
      }
      surface.material.uniforms.image = map.image;
      surface.primitive.show = true;
      applyStyle();
      publish({ status: 'Loaded', classes: data.classes });

      if (probe) {
        sampleAt(probe);
      }
    } catch (cause) {
      if (disposed || request !== generation) {
        return;
      }

      const message = cause instanceof Error ? cause.message : 'Noise maps could not load';
      console.error('Noise results failed', cause);
      publish({ status: 'Unavailable', error: message });
    }
  }

  const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction((event: { position: Cartesian2 }) => {
    if (!options.enabled || !current || disposed) {
      return;
    }

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
    if (!position) {
      return;
    }

    const geographic = Cartographic.fromCartesian(position);
    probe = {
      longitude: CesiumMath.toDegrees(geographic.longitude),
      latitude: CesiumMath.toDegrees(geographic.latitude),
    };
    sampleAt(probe);
    onProbe(probe);
  }, ScreenSpaceEventType.LEFT_CLICK);

  const removeUpdate = viewer.scene.postUpdate.addEventListener(() => {
    if (surface?.primitive.show && !surface.primitive.ready) {
      viewer.scene.requestRender();
    }
  });

  return {
    setOptions(value: NoiseOptions) {
      const styleOnly = options.enabled === value.enabled && options.period === value.period
        && options.retryRequest === value.retryRequest;
      options = value;

      if (styleOnly) {
        applyStyle();
      } else {
        void refresh();
      }
    },
    setScenario(value: ScenarioId) {
      scenario = value;
      void refresh();
    },
    setProbe(point: NoiseLocation | null) {
      probe = point;
      sampleGeneration++;
      if (point) {
        sampleAt(point);
      } else {
        publish({ sample: null });
      }
    },
    dispose() {
      disposed = true;
      generation++;
      sampleGeneration++;
      abort.abort();
      removeUpdate();
      handler.destroy();
      viewer.scene.primitives.remove(collection);

      if (surface && !surface.material.isDestroyed()) {
        surface.material.destroy();
      }
    },
  };
}

export type NoiseLayer = ReturnType<typeof createNoiseLayer>;
