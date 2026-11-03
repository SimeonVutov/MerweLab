import type { Viewer } from 'cesium';
import { useEffect, useRef, useState } from 'react';
import type { CbsOptions } from '../features/cbs/data';
import type { EnvironmentInfo, EnvironmentOptions } from '../features/environment/types';
import { hasLandUseLayers } from '../features/landUse/types';
import type { LandUseLocation, LandUseOptions, LandUsePane } from '../features/landUse/types';
import { hasMorphologyLayers } from '../features/morphology/data';
import type { MorphologyOptions } from '../features/morphology/data';
import type { NetworkInfo, NetworkOptions, NetworkPane } from '../features/network/types';
import type { NoiseInfo, NoiseLocation, NoiseOptions } from '../features/noise/types';
import type { WindInfo, WindLocation, WindOptions } from '../features/wind/types';
import type { ScenarioId } from '../project';
import type { ViewMode } from './camera';
import type { ModelStatus } from './modelLayers';
import { createSceneController } from './sceneController';
import type { SceneController } from './sceneController';
import type { TerrainStatus } from './terrain';
import styles from './CesiumScene.module.css';

// Each map pane owns a viewer; feature settings and callbacks come from App.
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
    const container = useRef<HTMLDivElement>(null);
    const controller = useRef<SceneController | null>(null);

    // Long-lived scene handlers read the latest callbacks without recreating the viewer.
    const environmentInfoCallback = useRef(onEnvironmentInfo);
    const landUseProbeCallback = useRef(onLandUseProbe);
    const cbsSelect = useRef(onCbsSelect);
    const onWindProbeRef = useRef(onWindProbe);
    const noiseProbeCallback = useRef(onNoiseProbe);
    const networkInfoCallback = useRef(onNetworkInfo);

    environmentInfoCallback.current = onEnvironmentInfo;
    landUseProbeCallback.current = onLandUseProbe;
    cbsSelect.current = onCbsSelect;
    onWindProbeRef.current = onWindProbe;
    noiseProbeCallback.current = onNoiseProbe;
    networkInfoCallback.current = onNetworkInfo;

    const [error, setError] = useState<string | null>(null);
    const [imageryError, setImageryError] = useState<string | null>(null);
    const [terrainError, setTerrainError] = useState<string | null>(null);
    const [contextError, setContextError] = useState(false);
    const [outlineError, setOutlineError] = useState<string | null>(null);
    const [morphologyError, setMorphologyError] = useState<string | null>(null);
    const [landUseError, setLandUseError] = useState<string | null>(null);
    const [cbsError, setCbsError] = useState<string | null>(null);

    // Create and dispose the viewer and its layers together so no handlers outlive the scene.
    useEffect(() => {
        if (!container.current) {
            return;
        }

        try {
            controller.current = createSceneController(container.current, {
                onEnvironmentInfo: (info) => environmentInfoCallback.current(info),
                onLandUseProbe: (point) => landUseProbeCallback.current(point),
                onNetworkInfo: (info) => networkInfoCallback.current(info),
                onCbsSelect: (id) => cbsSelect.current(id),
                onWindProbe: (point) => onWindProbeRef.current?.(point),
                onNoiseProbe: (point) => noiseProbeCallback.current?.(point),
                onViewerReady,
                onBuildingStatus,
                onSurfaceStatus,
                onTerrainStatus,
                onWindInfo,
                onNoiseInfo,
                setError,
                setImageryError,
                setTerrainError,
                setContextError,
                setOutlineError,
                setMorphologyError,
                setLandUseError,
                setCbsError,
            });
        } catch (cause) {
            console.error('Cesium initialization failed', cause);
            setError('The 3D view could not start. Check that WebGL is enabled in your browser.');
            return;
        }

        return () => {
            controller.current?.dispose();
            controller.current = null;
        };
    }, [onBuildingStatus, onSurfaceStatus, onTerrainStatus, onWindInfo, onViewerReady, onNoiseInfo]);

    // Repeat these updates after a viewer rebuild as well as after a scenario change.
    useEffect(() => {
        controller.current?.setScenario(scenarioId);
    }, [
        scenarioId,
        onBuildingStatus,
        onSurfaceStatus,
        onTerrainStatus,
        onWindInfo,
        onViewerReady,
        onNoiseInfo,
    ]);

    useEffect(() => {
        controller.current?.setWind(wind);
    }, [wind, onBuildingStatus, onSurfaceStatus, onTerrainStatus, onWindInfo, onViewerReady, onNoiseInfo]);

    // Layer changes must not reset a camera the user has already moved.
    useEffect(() => {
        controller.current?.setView(viewMode, viewRequest);
    }, [viewMode, viewRequest, onViewerReady]);

    useEffect(() => {
        controller.current?.setEnvironment(environment, viewMode);
    }, [environment, viewMode, onViewerReady]);

    useEffect(() => {
        controller.current?.setMorphology(morphology);
    }, [morphology, onViewerReady]);

    useEffect(() => {
        controller.current?.setLandUse(landUse, landUsePane);
    }, [landUse, landUsePane, onViewerReady]);

    useEffect(() => {
        controller.current?.setNoise(noise);
    }, [noise, onNoiseInfo, onViewerReady]);

    useEffect(() => {
        controller.current?.setNetwork(network, networkPane);
    }, [network, networkPane, onViewerReady]);

    useEffect(() => {
        controller.current?.setNoiseProbe(noiseProbe ?? null);
    }, [noiseProbe, onNoiseInfo, onViewerReady]);

    useEffect(() => {
        controller.current?.setCbs(cbs);
    }, [cbs, onViewerReady]);

    useEffect(() => {
        controller.current?.setWindProbe(windProbe ?? null);
    }, [windProbe, onViewerReady]);

    useEffect(() => {
        controller.current?.setBuildings(contextVisible, scenarioVisible, viewMode, scenarioId);
    }, [
        contextVisible,
        scenarioVisible,
        viewMode,
        scenarioId,
        onBuildingStatus,
        onSurfaceStatus,
        onTerrainStatus,
        onWindInfo,
        onViewerReady,
        onNoiseInfo,
    ]);

    useEffect(() => {
        controller.current?.setSurfaces(groundVisible, waterVisible);
    }, [
        groundVisible,
        waterVisible,
        onBuildingStatus,
        onSurfaceStatus,
        onTerrainStatus,
        onWindInfo,
        onViewerReady,
        onNoiseInfo,
    ]);

    useEffect(() => {
        controller.current?.setImagery(imageryVisible, imageryOpacity);
    }, [
        imageryVisible,
        imageryOpacity,
        onBuildingStatus,
        onSurfaceStatus,
        onTerrainStatus,
        onWindInfo,
        onViewerReady,
        onNoiseInfo,
    ]);

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
                <button
                    disabled={error !== null}
                    onClick={() => controller.current?.resetView(viewMode)}
                >
                    Reset view
                </button>
                <div role="group" aria-label="Building view mode">
                    <button aria-pressed={viewMode === '2d'} onClick={() => onViewModeChange('2d')}>2D</button>
                    <button aria-pressed={viewMode === '3d'} onClick={() => onViewModeChange('3d')}>3D</button>
                </div>
            </div>
            <div className={styles.location}>Merwehaven · {scenarioLabel}</div>
            {terrainError && !error && (
                <p className={styles.message} role="alert">{terrainError}</p>
            )}
            {imageryError && imageryVisible && !terrainError && !error && (
                <p className={styles.message} role="status">{imageryError}</p>
            )}
            {contextError && contextVisible && !imageryError && !terrainError && !error && (
                <p className={styles.message} role="status">Some surrounding buildings could not load.</p>
            )}
            {error && <p className={styles.message} role="alert">{error}</p>}
            {cbsError && cbs.enabled && !error && (
                <p className={styles.message} role="alert">{cbsError}</p>
            )}
        </>
    );
}
