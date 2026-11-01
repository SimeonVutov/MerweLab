import { useEffect, useRef, useState } from 'react';
import type { ImageryLayer, Viewer } from 'cesium';
import { createViewer } from './createViewer';
import { createAerialImagery, createGlobeImagery } from './imagery';
import { resetCamera } from './camera';
import styles from './CesiumScene.module.css';
import { createModelLayers } from './modelLayers';
import type { ModelLayers, ModelStatus } from './modelLayers';
import type { ScenarioId } from '../project';
import { createTerrainLayer } from './terrain';
import type { TerrainLayer, TerrainStatus } from './terrain';
import { createContextBuildings } from './contextBuildings';
import type { ContextBuildings } from './contextBuildings';

interface CesiumSceneProps {
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
}

export default function CesiumScene({ scenarioLabel, imageryVisible, imageryOpacity, scenarioId, contextVisible, scenarioVisible, onBuildingStatus,
  groundVisible, waterVisible, onSurfaceStatus, onTerrainStatus,
}: CesiumSceneProps) {
  const container = useRef<HTMLDivElement>(null);
  const viewer = useRef<Viewer | null>(null);
  const imagery = useRef<ImageryLayer | null>(null);
  const buildings = useRef<ModelLayers | null>(null);
  const surfaces = useRef<ModelLayers | null>(null);
  const terrain = useRef<TerrainLayer | null>(null);
  const context = useRef<ContextBuildings | null>(null);
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
    const resizeObserver = new ResizeObserver(() => {
      instance.resize();
      instance.scene.requestRender();
    });
    resizeObserver.observe(container.current);

    return () => {
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
      imagery.current = null;
      viewer.current = null;
      instance.destroy();
    };
  }, [onBuildingStatus, onSurfaceStatus, onTerrainStatus]);

  useEffect(() => {
    buildings.current?.setScenario(scenarioId);
    surfaces.current?.setScenario(scenarioId);
  }, [scenarioId, onBuildingStatus, onSurfaceStatus, onTerrainStatus]);

  useEffect(() => {
    buildings.current?.setVisibility(contextVisible, scenarioVisible);
    context.current?.setVisible(contextVisible);
  }, [contextVisible, scenarioVisible, onBuildingStatus, onSurfaceStatus, onTerrainStatus]);

  useEffect(() => {
    surfaces.current?.setVisibility(groundVisible, groundVisible, waterVisible);
    terrain.current?.setSiteVisible(groundVisible);
  }, [groundVisible, waterVisible, onBuildingStatus, onSurfaceStatus, onTerrainStatus]);

  useEffect(() => {
    if (!viewer.current || !imagery.current) return;
    imagery.current.show = imageryVisible;
    imagery.current.alpha = imageryOpacity;
    viewer.current.scene.requestRender();
  }, [imageryVisible, imageryOpacity, onBuildingStatus, onSurfaceStatus, onTerrainStatus]);

  return (
    <>
      <div ref={container} className={styles.canvas} />
      <div className={styles.toolbar}>
        <button disabled={error !== null} onClick={() => viewer.current && resetCamera(viewer.current)}>Reset view</button>
      </div>
      <div className={styles.location}>Merwehaven · {scenarioLabel}</div>
      {terrainError && !error && <p className={styles.message} role="alert">{terrainError}</p>}
      {imageryError && imageryVisible && !terrainError && !error && <p className={styles.message} role="status">{imageryError}</p>}
      {contextError && contextVisible && !imageryError && !terrainError && !error && <p className={styles.message} role="status">Some surrounding buildings could not load.</p>}
      {error && <p className={styles.message} role="alert">{error}</p>}
    </>
  );
}
