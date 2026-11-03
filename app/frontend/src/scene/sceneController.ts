import type { Viewer } from 'cesium';
import type { CbsOptions } from '../features/cbs/data';
import { createCbsLayer } from '../features/cbs/scene';
import { createEnvironmentLayers } from '../features/environment/scene';
import type { EnvironmentInfo, EnvironmentOptions } from '../features/environment/types';
import { createLandUseLayers } from '../features/landUse/scene';
import type { LandUseLocation, LandUseOptions, LandUsePane } from '../features/landUse/types';
import type { MorphologyOptions } from '../features/morphology/data';
import { createMorphologyLayer } from '../features/morphology/scene';
import { createNetworkLayer } from '../features/network/scene';
import type { NetworkInfo, NetworkOptions, NetworkPane } from '../features/network/types';
import { createNoiseLayer } from '../features/noise/scene';
import type { NoiseInfo, NoiseLocation, NoiseOptions } from '../features/noise/types';
import { createWindLayer } from '../features/wind/scene';
import type { WindInfo, WindLocation, WindOptions } from '../features/wind/types';
import type { ScenarioId } from '../project';
import { createBuildingOutlines } from './buildingOutlines';
import { resetCamera } from './camera';
import type { ViewMode } from './camera';
import { createContextBuildings } from './contextBuildings';
import { createViewer } from './createViewer';
import { createAerialImagery, createGlobeImagery } from './imagery';
import { createModelLayers } from './modelLayers';
import type { ModelStatus } from './modelLayers';
import { createTerrainLayer } from './terrain';
import type { TerrainStatus } from './terrain';


export interface SceneCallbacks {
    onEnvironmentInfo: (info: EnvironmentInfo) => void;
    onLandUseProbe: (point: LandUseLocation) => void;
    onNetworkInfo: (info: NetworkInfo) => void;
    onCbsSelect: (id: string) => void;
    onWindProbe?: (point: WindLocation) => void;
    onNoiseProbe?: (point: NoiseLocation) => void;
    onViewerReady?: (viewer: Viewer | null) => void;
    onBuildingStatus: (status: ModelStatus) => void;
    onSurfaceStatus: (status: ModelStatus) => void;
    onTerrainStatus: (status: TerrainStatus) => void;
    onWindInfo: (info: WindInfo) => void;
    onNoiseInfo: (info: NoiseInfo) => void;
    setError: (message: string | null) => void;
    setImageryError: (message: string | null) => void;
    setTerrainError: (message: string | null) => void;
    setContextError: (failed: boolean) => void;
    setOutlineError: (message: string | null) => void;
    setMorphologyError: (message: string | null) => void;
    setLandUseError: (message: string | null) => void;
    setCbsError: (message: string | null) => void;
}

// Each map pane owns one controller. Feature modules retain their own loading and rendering logic.
export function createSceneController(container: HTMLDivElement, events: SceneCallbacks) {
    const instance = createViewer(container);
    const rollback: (() => void)[] = [() => instance.destroy()];

    try {
        const environmentLayers = createEnvironmentLayers(instance, (info) => events.onEnvironmentInfo(info));
        rollback.push(() => environmentLayers.dispose());
        const outlines = createBuildingOutlines(instance, events.setOutlineError);
        rollback.push(() => outlines.dispose());
        const morphologyLayer = createMorphologyLayer(instance, events.setMorphologyError);
        rollback.push(() => morphologyLayer.dispose());
        const landUseLayers = createLandUseLayers(instance, (point) => events.onLandUseProbe(point), events.setLandUseError);
        rollback.push(() => landUseLayers.dispose());
        events.onViewerReady?.(instance);
        rollback.push(() => events.onViewerReady?.(null));
        events.setError(null);
        events.setImageryError(null);
        events.setTerrainError(null);
        events.setContextError(false);

        const base = createGlobeImagery();
        const aerial = createAerialImagery();
        const removeBaseError = base.errorEvent.addEventListener(() => {
            events.setImageryError('Overview imagery could not load.');
        });
        rollback.push(removeBaseError);
        const removeAerialError = aerial.imageryProvider.errorEvent.addEventListener(() => {
            events.setImageryError('Some aerial imagery could not load. Check your connection to PDOK.');
        });
        rollback.push(removeAerialError);
        const removeRenderError = instance.scene.renderError.addEventListener(() => {
            events.setError('The 3D view stopped rendering. Reload the page to try again.');
        });
        rollback.push(removeRenderError);

        instance.imageryLayers.add(base);
        instance.imageryLayers.add(aerial);

        const buildings = createModelLayers(instance, 'buildings', events.onBuildingStatus);
        rollback.push(() => buildings.dispose());
        const terrain = createTerrainLayer(instance, events.onTerrainStatus, events.setTerrainError);
        rollback.push(() => terrain.dispose());
        // Hide shared terrain only once the replacement site surface has finished loading.
        const surfaces = createModelLayers(instance, 'surfaces', (status) => {
            events.onSurfaceStatus(status);
            terrain.setSiteReady(status.scenario === 'Loaded');
        });
        rollback.push(() => surfaces.dispose());
        const context = createContextBuildings(instance, () => events.setContextError(true));
        rollback.push(() => context.dispose());
        const windLayer = createWindLayer(instance, events.onWindInfo, (point) => events.onWindProbe?.(point));
        rollback.push(() => windLayer.dispose());
        const cbsLayer = createCbsLayer(instance, (id) => events.onCbsSelect(id), events.setCbsError);
        rollback.push(() => cbsLayer.dispose());
        const noiseLayer = createNoiseLayer(instance, events.onNoiseInfo, (point) => events.onNoiseProbe?.(point));
        rollback.push(() => noiseLayer.dispose());
        const networkLayer = createNetworkLayer(instance, (info) => events.onNetworkInfo(info));
        rollback.push(() => networkLayer.dispose());

        const resizeObserver = new ResizeObserver(() => {
            instance.resize();
            instance.scene.requestRender();
        });
        rollback.push(() => resizeObserver.disconnect());
        resizeObserver.observe(container);

        let cameraMode: ViewMode | null = null;
        let cameraRequest: number | null = null;
        let disposed = false;

        return {
            setScenario(scenario: ScenarioId) {
                morphologyLayer.setScenario(scenario);
                buildings.setScenario(scenario);
                surfaces.setScenario(scenario);
                windLayer.setScenario(scenario);
                noiseLayer.setScenario(scenario);
                networkLayer.setScenario(scenario);
            },
            setView(mode: ViewMode, request: number) {
                // Layer updates keep the current camera; only mode changes and explicit requests reset it.
                if (cameraMode === mode && cameraRequest === request) {
                    return;
                }

                cameraMode = mode;
                cameraRequest = request;
                resetCamera(instance, mode);
            },
            resetView(mode: ViewMode) {
                resetCamera(instance, mode);
            },
            setEnvironment(options: EnvironmentOptions, mode: ViewMode) {
                environmentLayers.setOptions(options, mode);
            },
            setMorphology(options: MorphologyOptions) {
                morphologyLayer.setOptions(options);
            },
            setLandUse(options: LandUseOptions, pane: LandUsePane) {
                landUseLayers.setOptions(options, pane);
            },
            setWind(options: WindOptions) {
                windLayer.setOptions(options);
            },
            setNoise(options: NoiseOptions) {
                noiseLayer.setOptions(options);
            },
            setNetwork(options: NetworkOptions, pane: NetworkPane) {
                networkLayer.setOptions(options, pane);
            },
            setCbs(options: CbsOptions) {
                cbsLayer.setOptions(options);
            },
            setWindProbe(point: WindLocation | null) {
                windLayer.setProbe(point);
            },
            setNoiseProbe(point: NoiseLocation | null) {
                noiseLayer.setProbe(point);
            },
            setBuildings(contextVisible: boolean, scenarioVisible: boolean, mode: ViewMode, scenario: ScenarioId) {
                buildings.setVisibility(contextVisible && mode === '3d', scenarioVisible && mode === '3d');
                context.setVisible(contextVisible && mode === '3d');
                outlines.setOptions(mode === '2d', scenario, contextVisible, scenarioVisible);
            },
            setSurfaces(groundVisible: boolean, waterVisible: boolean) {
                surfaces.setVisibility(groundVisible, groundVisible, waterVisible);
                terrain.setSiteVisible(groundVisible);
            },
            setImagery(visible: boolean, opacity: number) {
                aerial.show = visible;
                aerial.alpha = opacity;
                instance.scene.requestRender();
            },
            dispose() {
                if (disposed) {
                    return;
                }
                disposed = true;

                events.onViewerReady?.(null);
                environmentLayers.dispose();
                morphologyLayer.dispose();
                landUseLayers.dispose();
                outlines.dispose();
                resizeObserver.disconnect();
                removeBaseError();
                removeAerialError();
                removeRenderError();
                buildings.dispose();
                surfaces.dispose();
                terrain.dispose();
                context.dispose();
                windLayer.dispose();
                cbsLayer.dispose();
                noiseLayer.dispose();
                networkLayer.dispose();
                instance.destroy();
            },
        };
    } catch (cause) {
        // A synchronous setup failure must also release resources created before it.
        for (const release of rollback.reverse()) {
            release();
        }
        throw cause;
    }
}

export type SceneController = ReturnType<typeof createSceneController>;
