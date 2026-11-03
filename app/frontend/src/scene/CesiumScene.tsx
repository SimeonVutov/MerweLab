import { useEffect, useRef, useState } from 'react';
import { createNetworkLayer } from '../features/network/scene';
import type { NetworkInfo, NetworkOptions, NetworkPane } from '../features/network/types';
import { createLandUseLayers } from '../features/landUse/scene';
import { hasLandUseLayers } from '../features/landUse/types';
import type { LandUseLocation, LandUseOptions, LandUsePane } from '../features/landUse/types';
import type { ImageryLayer, Viewer } from 'cesium';
import { createEnvironmentLayers } from '../features/environment/scene';
import type { EnvironmentInfo, EnvironmentOptions } from '../features/environment/types';
import { createMorphologyLayer } from '../features/morphology/scene';
import { hasMorphologyLayers } from '../features/morphology/data';
import type { MorphologyOptions } from '../features/morphology/data';
import { createViewer } from './createViewer';
import { createNoiseLayer } from '../features/noise/scene';
import type { NoiseLayer } from '../features/noise/scene';
import type { NoiseInfo, NoiseLocation, NoiseOptions } from '../features/noise/types';
import { createCbsLayer } from '../features/cbs/scene';
import type { CbsOptions } from '../features/cbs/data';
import { createAerialImagery, createGlobeImagery } from './imagery';
import { createBuildingOutlines } from './buildingOutlines';
import type { ViewMode } from './camera';
import { resetCamera } from './camera';
import styles from './CesiumScene.module.css';
import { createModelLayers } from './modelLayers';
import type { ModelLayers, ModelStatus } from './modelLayers';
import type { ScenarioId } from '../project';
import { createTerrainLayer } from './terrain';
import type { TerrainLayer, TerrainStatus } from './terrain';
import { createContextBuildings } from './contextBuildings';
import type { ContextBuildings } from './contextBuildings';
import { createWindLayer } from '../features/wind/scene';
import type { WindLayer } from '../features/wind/scene';
import type { WindInfo, WindLocation, WindOptions } from '../features/wind/types';

interface CesiumSceneProps {
  network: NetworkOptions;
  networkPane: NetworkPane;
  onNetworkInfo: (info: NetworkInfo) => void;
  landUse: LandUseOptions;
  landUsePane: LandUsePane;
  onLandUseProbe: (point: LandUseLocation) => void;
  environment: EnvironmentOptions;
  onEnvironmentInfo: (info: EnvironmentInfo) => void;
  viewMode: ViewMode;
  viewRequest: number;
  onViewModeChange: (mode: ViewMode) => void;
  morphology: MorphologyOptions;
  noise: NoiseOptions;
  onNoiseInfo: (info: NoiseInfo) => void;
  noiseProbe?: NoiseLocation | null;
  onNoiseProbe?: (point: NoiseLocation) => void;
  cbs: CbsOptions;
  onCbsSelect: (id: string) => void;
  scenarioLabel: string;
  imageryVisible: boolean;
  imageryOpacity: number;
  scenarioId: ScenarioId;
  contextVisible: boolean;
  scenarioVisible: boolean;
  onBuildingStatus: (status: ModelStatus) => void;
  groundVisible: boolean;
  waterVisible: boolean;
  onSurfaceStatus: (status: ModelStatus) => void;
  onTerrainStatus: (status: TerrainStatus) => void;
  wind: WindOptions;
  onWindInfo: (info: WindInfo) => void;
  onViewerReady?: (viewer: Viewer | null) => void;
  windProbe?: WindLocation | null;
  onWindProbe?: (point: WindLocation) => void;
}

export default function CesiumScene({
  network,
  networkPane,
  onNetworkInfo,
  landUse,
  landUsePane,
  onLandUseProbe,
  environment,
  onEnvironmentInfo,
  morphology,
  viewMode,
  viewRequest,
  onViewModeChange,
  scenarioLabel,
  imageryVisible,
  imageryOpacity,
  scenarioId,
  contextVisible,
  scenarioVisible,
  onBuildingStatus,
  groundVisible,
  waterVisible,
  onSurfaceStatus,
  onTerrainStatus,
  wind,
  onWindInfo,
  onViewerReady,
  windProbe,
  onWindProbe,
  cbs,
  onCbsSelect,
  noise,
  onNoiseInfo,
  noiseProbe,
  onNoiseProbe,
}: CesiumSceneProps) {
  const networkLayer = useRef<ReturnType<typeof createNetworkLayer> | null>(null);
  const networkInfoCallback = useRef(onNetworkInfo);
  networkInfoCallback.current = onNetworkInfo;
  const landUseLayers = useRef<ReturnType<typeof createLandUseLayers> | null>(null);
  const landUseProbeCallback = useRef(onLandUseProbe);
  landUseProbeCallback.current = onLandUseProbe;
  const [landUseError, setLandUseError] = useState<string | null>(null);
  const environmentLayers = useRef<ReturnType<typeof createEnvironmentLayers> | null>(null);
  const environmentInfoCallback = useRef(onEnvironmentInfo);
  environmentInfoCallback.current = onEnvironmentInfo;

  const morphologyLayer = useRef<ReturnType<typeof createMorphologyLayer> | null>(null);
  const [morphologyError, setMorphologyError] = useState<string | null>(null);
  const outlines = useRef<ReturnType<typeof createBuildingOutlines> | null>(null);
  const [outlineError, setOutlineError] = useState<string | null>(null);
  const cameraMode = useRef<ViewMode | null>(null);
  const cameraRequest = useRef<number | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const viewer = useRef<Viewer | null>(null);
  const imagery = useRef<ImageryLayer | null>(null);
  const buildings = useRef<ModelLayers | null>(null);
  const surfaces = useRef<ModelLayers | null>(null);
  const terrain = useRef<TerrainLayer | null>(null);
  const context = useRef<ContextBuildings | null>(null);
  const windLayer = useRef<WindLayer | null>(null);
  const cbsLayer = useRef<ReturnType<typeof createCbsLayer> | null>(null);
  const noiseLayer = useRef<NoiseLayer | null>(null);
  const noiseProbeCallback = useRef(onNoiseProbe);
  noiseProbeCallback.current = onNoiseProbe;
  const cbsSelect = useRef(onCbsSelect);

  cbsSelect.current = onCbsSelect;

  const [cbsError, setCbsError] = useState<string | null>(null);
  const onWindProbeRef = useRef(onWindProbe);
  onWindProbeRef.current = onWindProbe;
  const [contextError, setContextError] = useState(false);
  const [terrainError, setTerrainError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imageryError, setImageryError] = useState<string | null>(null);

  useEffect(() => {
    if (!container.current) return;
    let instance: Viewer;
    try {
      instance = createViewer(container.current);
    } catch (cause) {
      console.error('Cesium initialization failed', cause);
      setError('The 3D view could not start. Check that WebGL is enabled in your browser.');
      return;
    }

    viewer.current = instance;
    environmentLayers.current = createEnvironmentLayers(instance, (info) => environmentInfoCallback.current(info));
    outlines.current = createBuildingOutlines(instance, setOutlineError);
    morphologyLayer.current = createMorphologyLayer(instance, setMorphologyError);
    landUseLayers.current = createLandUseLayers(instance, (point) => landUseProbeCallback.current(point), setLandUseError);
    onViewerReady?.(instance);
    setError(null);
    setImageryError(null);
    setTerrainError(null);
    setContextError(false);
    const base = createGlobeImagery();
    const aerial = createAerialImagery();
    const removeBaseError = base.errorEvent.addEventListener(() => {
      setImageryError('Overview imagery could not load.');
    });
    const removeAerialError = aerial.imageryProvider.errorEvent.addEventListener(() => {
      setImageryError('Some aerial imagery could not load. Check your connection to PDOK.');
    });
    const removeRenderError = instance.scene.renderError.addEventListener(() => {
      setError('The 3D view stopped rendering. Reload the page to try again.');
    });
    instance.imageryLayers.add(base);
    instance.imageryLayers.add(aerial);
    imagery.current = aerial;
    buildings.current = createModelLayers(instance, 'buildings', onBuildingStatus);
    terrain.current = createTerrainLayer(instance, onTerrainStatus, setTerrainError);
    surfaces.current = createModelLayers(instance, 'surfaces', (status) => {
      onSurfaceStatus(status);
      terrain.current?.setSiteReady(status.scenario === 'Loaded');
    });
    context.current = createContextBuildings(instance, () => setContextError(true));
    windLayer.current = createWindLayer(instance, onWindInfo, (point) => onWindProbeRef.current?.(point));
    cbsLayer.current = createCbsLayer(instance, (id) => cbsSelect.current(id), setCbsError);
    noiseLayer.current = createNoiseLayer(instance, onNoiseInfo, (point) => noiseProbeCallback.current?.(point));
    networkLayer.current = createNetworkLayer(instance, (info) => networkInfoCallback.current(info));
    const resizeObserver = new ResizeObserver(() => {
      instance.resize();
      instance.scene.requestRender();
    });
    resizeObserver.observe(container.current);

    return () => {
      onViewerReady?.(null);
      environmentLayers.current?.dispose();
      environmentLayers.current = null;
      morphologyLayer.current?.dispose();
      morphologyLayer.current = null;
      landUseLayers.current?.dispose();
      landUseLayers.current = null;
      outlines.current?.dispose();
      outlines.current = null;
      resizeObserver.disconnect();
      removeBaseError();
      removeAerialError();
      removeRenderError();
      buildings.current?.dispose();
      buildings.current = null;
      surfaces.current?.dispose();
      surfaces.current = null;
      terrain.current?.dispose();
      terrain.current = null;
      context.current?.dispose();
      context.current = null;
      windLayer.current?.dispose();
      windLayer.current = null;
      cbsLayer.current?.dispose();
      cbsLayer.current = null;
      noiseLayer.current?.dispose();
      noiseLayer.current = null;
      networkLayer.current?.dispose();
      networkLayer.current = null;
      imagery.current = null;
      viewer.current = null;
      cameraMode.current = null;
      instance.destroy();
    };
  }, [onBuildingStatus, onSurfaceStatus, onTerrainStatus, onWindInfo, onViewerReady, onNoiseInfo]);

  useEffect(() => {
    morphologyLayer.current?.setScenario(scenarioId);
    buildings.current?.setScenario(scenarioId);
    surfaces.current?.setScenario(scenarioId);
    windLayer.current?.setScenario(scenarioId);
    noiseLayer.current?.setScenario(scenarioId);
    networkLayer.current?.setScenario(scenarioId);
  }, [scenarioId, onBuildingStatus, onSurfaceStatus, onTerrainStatus, onWindInfo, onViewerReady, onNoiseInfo]);

  useEffect(() => {
    windLayer.current?.setOptions(wind);
  }, [wind, onBuildingStatus, onSurfaceStatus, onTerrainStatus, onWindInfo, onViewerReady, onNoiseInfo]);

  useEffect(() => {
    if (viewer.current && (cameraMode.current !== viewMode || cameraRequest.current !== viewRequest)) {
      cameraMode.current = viewMode;
      cameraRequest.current = viewRequest;
      resetCamera(viewer.current, viewMode);
    }
  }, [viewMode, viewRequest, onViewerReady]);

  useEffect(() => {
    environmentLayers.current?.setOptions(environment, viewMode);
  }, [environment, viewMode, onViewerReady]);

  useEffect(() => {
    morphologyLayer.current?.setOptions(morphology);
  }, [morphology, onViewerReady]);

  useEffect(() => {
    landUseLayers.current?.setOptions(landUse, landUsePane);
  }, [landUse, landUsePane, onViewerReady]);

  useEffect(() => {
    noiseLayer.current?.setOptions(noise);
  }, [noise, onNoiseInfo, onViewerReady]);

  useEffect(() => {
    networkLayer.current?.setOptions(network, networkPane);
  }, [network, networkPane, onViewerReady]);

  useEffect(() => {
    noiseLayer.current?.setProbe(noiseProbe ?? null);
  }, [noiseProbe, onNoiseInfo, onViewerReady]);

  useEffect(() => {
    cbsLayer.current?.setOptions(cbs);
  }, [cbs, onViewerReady]);

  useEffect(() => {
    windLayer.current?.setProbe(windProbe ?? null);
  }, [windProbe, onViewerReady]);

  useEffect(() => {
    buildings.current?.setVisibility(contextVisible && viewMode === '3d', scenarioVisible && viewMode === '3d');
    context.current?.setVisible(contextVisible && viewMode === '3d');
    outlines.current?.setOptions(viewMode === '2d', scenarioId, contextVisible, scenarioVisible);
  }, [contextVisible, scenarioVisible, viewMode, scenarioId, onBuildingStatus, onSurfaceStatus, onTerrainStatus, onWindInfo, onViewerReady, onNoiseInfo]);

  useEffect(() => {
    surfaces.current?.setVisibility(groundVisible, groundVisible, waterVisible);
    terrain.current?.setSiteVisible(groundVisible);
  }, [groundVisible, waterVisible, onBuildingStatus, onSurfaceStatus, onTerrainStatus, onWindInfo, onViewerReady, onNoiseInfo]);

  useEffect(() => {
    if (!viewer.current || !imagery.current) return;
    imagery.current.show = imageryVisible;
    imagery.current.alpha = imageryOpacity;
    viewer.current.scene.requestRender();
  }, [imageryVisible, imageryOpacity, onBuildingStatus, onSurfaceStatus, onTerrainStatus, onWindInfo, onViewerReady, onNoiseInfo]);

  return (
    <>
      {landUseError && hasLandUseLayers(landUse) && (
        <p className={styles.message} role="alert">{landUseError}</p>
      )}
      {morphologyError && hasMorphologyLayers(morphology) && (
        <p className={styles.message} role="alert">{morphologyError}</p>
      )}
      {outlineError && viewMode === '2d' && (
        <p className={styles.message} role="alert">{outlineError}</p>
      )}
      <div ref={container} className={styles.canvas} />
      <div className={styles.toolbar}>
        <button disabled={error !== null} onClick={() => viewer.current && resetCamera(viewer.current, viewMode)}>Reset view</button>
        <div role="group" aria-label="Building view mode">
          <button aria-pressed={viewMode === '2d'} onClick={() => onViewModeChange('2d')}>2D</button>
          <button aria-pressed={viewMode === '3d'} onClick={() => onViewModeChange('3d')}>3D</button>
        </div>
      </div>
      <div className={styles.location}>Merwehaven · {scenarioLabel}</div>
      {terrainError && !error && <p className={styles.message} role="alert">{terrainError}</p>}
      {imageryError && imageryVisible && !terrainError && !error && <p className={styles.message} role="status">{imageryError}</p>}
      {contextError && contextVisible && !imageryError && !terrainError && !error && <p className={styles.message} role="status">Some surrounding buildings could not load.</p>}
      {error && <p className={styles.message} role="alert">{error}</p>}
      {cbsError && cbs.enabled && !error && (
        <p className={styles.message} role="alert">{cbsError}</p>
      )}
    </>
  );
}
