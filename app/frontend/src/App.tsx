import { useEffect, useState } from 'react';
import WeatherView from './features/weather/WeatherView';
import NetworkPanel from './features/network/NetworkPanel';
import { initialNetworkInfo, initialNetworkOptions } from './features/network/types';
import LandUsePanel from './features/landUse/LandUsePanel';
import { initialLandUseOptions } from './features/landUse/types';
import type { LandUseLocation } from './features/landUse/types';
import EnvironmentPanel from './features/environment/EnvironmentPanel';
import { initialEnvironmentInfo, initialEnvironmentOptions } from './features/environment/types';
import type { EnvironmentInfo } from './features/environment/types';
import type { ViewMode } from './scene/camera';
import type { Viewer } from 'cesium';
import CompareToolbar from './features/compare/CompareToolbar';
import { synchronizeCameras } from './features/compare/synchronizeCameras';
import { initialCbsOptions } from './features/cbs/data';
import type { CbsOptions } from './features/cbs/data';
import { initialNoiseInfo, initialNoiseOptions } from './features/noise/types';
import type { NoiseInfo, NoiseLocation, NoiseOptions } from './features/noise/types';
import MorphologyPanel from './features/morphology/MorphologyPanel';
import { initialMorphologyOptions } from './features/morphology/data';
import Header from './components/Header';
import LayerPanel from './components/LayerPanel';
import DetailsPanel from './components/DetailsPanel';
import CesiumScene from './scene/CesiumScene';
import { scenarios } from './project';
import type { Mode, ScenarioId } from './project';
import styles from './App.module.css';
import type { ModelStatus } from './scene/modelLayers';
import type { TerrainStatus } from './scene/terrain';
import { initialWindInfo, initialWindOptions } from './features/wind/types';
import type { WindInfo, WindLocation, WindOptions } from './features/wind/types';

export default function App() {
  const [network, setNetwork] = useState(initialNetworkOptions);
  const [networkInfo, setNetworkInfo] = useState(initialNetworkInfo);
  const [rightNetworkInfo, setRightNetworkInfo] = useState(initialNetworkInfo);
  const [landUse, setLandUse] = useState(initialLandUseOptions);
  const [landUseProbe, setLandUseProbe] = useState<LandUseLocation | null>(null);
  const [environment, setEnvironment] = useState(initialEnvironmentOptions);
  const [environmentInfo, setEnvironmentInfo] = useState<EnvironmentInfo>(initialEnvironmentInfo);
  const [rightEnvironmentInfo, setRightEnvironmentInfo] = useState<EnvironmentInfo>(initialEnvironmentInfo);
  const [mode, setMode] = useState<Mode>('Explore');
  const [viewMode, setViewMode] = useState<ViewMode>('3d');
  const [viewRequest, setViewRequest] = useState(0);
  const [morphology, setMorphology] = useState(initialMorphologyOptions);
  const [cbs, setCbs] = useState<CbsOptions>(initialCbsOptions);
  const [scenarioId, setScenarioId] = useState<ScenarioId>('scenario_a');
  const [rightScenarioId, setRightScenarioId] = useState<ScenarioId>('scenario_b');
  const [leftViewer, setLeftViewer] = useState<Viewer | null>(null);
  const [rightViewer, setRightViewer] = useState<Viewer | null>(null);
  const [rightTerrainStatus, setRightTerrainStatus] = useState<TerrainStatus>('Loading');
  const [rightBuildingStatus, setRightBuildingStatus] = useState<ModelStatus>({ context: 'Loading', scenario: 'Loading' });
  const [rightSurfaceStatus, setRightSurfaceStatus] = useState<ModelStatus>({ context: 'Loading', scenario: 'Loading', water: 'Loading' });
  const [rightWindInfo, setRightWindInfo] = useState<WindInfo>(initialWindInfo);
  const [windProbe, setWindProbe] = useState<WindLocation | null>(null);

  const [noise, setNoise] = useState<NoiseOptions>(initialNoiseOptions);
  const [noiseInfo, setNoiseInfo] = useState<NoiseInfo>(initialNoiseInfo);
  const [rightNoiseInfo, setRightNoiseInfo] = useState<NoiseInfo>(initialNoiseInfo);
  const [noiseProbe, setNoiseProbe] = useState<NoiseLocation | null>(null);

  const [layersOpen, setLayersOpen] = useState(true);
  const [detailsOpen, setDetailsOpen] = useState(true);
  const [imageryVisible, setImageryVisible] = useState(true);
  const [imageryOpacity, setImageryOpacity] = useState(1);
  const [contextVisible, setContextVisible] = useState(true);
  const [scenarioVisible, setScenarioVisible] = useState(true);
  const [groundVisible, setGroundVisible] = useState(true);
  const [waterVisible, setWaterVisible] = useState(false);
  const [terrainStatus, setTerrainStatus] = useState<TerrainStatus>('Loading');
  const [buildingStatus, setBuildingStatus] = useState<ModelStatus>({ context: 'Loading', scenario: 'Loading' });
  const [surfaceStatus, setSurfaceStatus] = useState<ModelStatus>({ context: 'Loading', scenario: 'Loading', water: 'Loading' });
  const [wind, setWind] = useState<WindOptions>(initialWindOptions);
  const [windInfo, setWindInfo] = useState<WindInfo>(initialWindInfo);
  const scenario = scenarios.find((item) => item.id === scenarioId)!;
  const rightScenario = scenarios.find((item) => item.id === rightScenarioId)!;
  const comparing = mode === 'Compare';
  const sceneSettings = {
    network,
    networkPane: 'left' as const,
    landUse,
    landUsePane: comparing ? 'left' as const : 'single' as const,
    onLandUseProbe: selectLandUsePoint,
    environment,
    morphology,
    viewMode,
    viewRequest,
    onViewModeChange: changeViewMode,
    imageryVisible,
    imageryOpacity,
    contextVisible,
    scenarioVisible,
    groundVisible,
    waterVisible,
    wind,
    windProbe: comparing ? windProbe : undefined,
    onWindProbe: setWindProbe,
    cbs,
    onCbsSelect: selectNeighbourhood,
    noise,
    noiseProbe: comparing ? noiseProbe : undefined,
    onNoiseProbe: setNoiseProbe,
  };

  function selectLandUsePoint(point: LandUseLocation) {
    setLandUseProbe(point);
    setDetailsOpen(true);
  }

  function selectNeighbourhood(id: string) {
    setCbs((current) => ({ ...current, selected: id }));
    setDetailsOpen(true);
  }

  function changeCbs(options: CbsOptions) {
    setCbs(options);
  }

  function changeMorphology(options: typeof morphology) {
    setMorphology(options);
  }

  function changeNoise(options: NoiseOptions) {
    setNoise(options);
  }

  function changeViewMode(value: ViewMode) {
    setViewMode(value);
    if (value === '2d') {
      setGroundVisible(false);
      setWind((current) => ({ ...current, streamlines_3d: false }));
    }
  }

  function changeWind(options: WindOptions) {
    if (options.streamlines_3d && !wind.streamlines_3d) {
      setViewMode('3d');
      setViewRequest((current) => current + 1);
    }
    setWind(options);
  }

  useEffect(() => {
    if (!comparing || !leftViewer || !rightViewer || leftViewer.isDestroyed() || rightViewer.isDestroyed()) {
      return;
    }

    return synchronizeCameras(leftViewer, rightViewer);
  }, [comparing, leftViewer, rightViewer]);

  useEffect(() => {
    if (networkInfo.selected || rightNetworkInfo.selected) setDetailsOpen(true);
  }, [networkInfo.selected, rightNetworkInfo.selected]);

  return (
    <div className={styles.app}>
      <a className={styles.skipLink} href={mode === 'Weather' ? '#weather' : '#scene'}>Skip to content</a>
      <Header
        mode={mode}
        scenarioId={scenarioId}
        onModeChange={setMode}
        onScenarioChange={setScenarioId}
      />
      <WeatherView hidden={mode !== 'Weather'} />
      <div
        hidden={mode === 'Weather'}
        className={styles.workspace}
        data-layers-open={layersOpen}
        data-details-open={detailsOpen}
      >
        <LayerPanel
          network={network}
          onNetworkChange={setNetwork}
          landUse={landUse}
          onLandUseChange={setLandUse}
          environment={environment}
          onEnvironmentChange={setEnvironment}
          morphology={morphology}
          onMorphologyChange={changeMorphology}
          noise={noise}
          onNoiseChange={changeNoise}
          cbs={cbs}
          onCbsChange={changeCbs}
          open={layersOpen}
          imageryVisible={imageryVisible}
          onImageryChange={setImageryVisible}
          contextVisible={contextVisible}
          scenarioVisible={scenarioVisible}
          onContextChange={setContextVisible}
          onScenarioChange={setScenarioVisible}
          groundVisible={groundVisible}
          waterVisible={waterVisible}
          onGroundChange={setGroundVisible}
          onWaterChange={setWaterVisible}
          wind={wind}
          onWindChange={changeWind}
        />
        <main id="scene" className={styles.scene} tabIndex={-1} aria-label="Merwehaven map">
          {comparing && <CompareToolbar left={scenarioId} right={rightScenarioId}
            onLeftChange={setScenarioId} onRightChange={setRightScenarioId}
            onSwap={() => { setScenarioId(rightScenarioId); setRightScenarioId(scenarioId); }} />}
          <div className={styles.views} data-comparing={comparing}>
            <section className={styles.view} aria-label={comparing ? `Left map: ${scenario.label}` : `Map: ${scenario.label}`}>
              <CesiumScene
                {...sceneSettings}
                scenarioLabel={scenario.label}
                scenarioId={scenarioId}
                onEnvironmentInfo={setEnvironmentInfo}
                onBuildingStatus={setBuildingStatus}
                onSurfaceStatus={setSurfaceStatus}
                onTerrainStatus={setTerrainStatus}
                onWindInfo={setWindInfo}
                onNoiseInfo={setNoiseInfo}
                onNetworkInfo={setNetworkInfo}
                onViewerReady={setLeftViewer}
              />
              <div className={styles.panelControls}>
                <button
                  aria-expanded={layersOpen}
                  aria-controls="layer-panel"
                  onClick={() => setLayersOpen((open) => !open)}
                >
                  Layers
                </button>
                <button
                  aria-expanded={detailsOpen}
                  aria-controls="details-panel"
                  onClick={() => setDetailsOpen((open) => !open)}
                >
                  Details
                </button>
              </div>
            </section>
            {comparing && <section className={styles.view} aria-label={`Right map: ${rightScenario.label}`}>
              <CesiumScene
                {...sceneSettings}
                networkPane="right"
                onNetworkInfo={setRightNetworkInfo}
                landUsePane="right"
                scenarioLabel={rightScenario.label}
                scenarioId={rightScenarioId}
                onEnvironmentInfo={setRightEnvironmentInfo}
                onBuildingStatus={setRightBuildingStatus}
                onSurfaceStatus={setRightSurfaceStatus}
                onTerrainStatus={setRightTerrainStatus}
                onWindInfo={setRightWindInfo}
                onNoiseInfo={setRightNoiseInfo}
                onViewerReady={setRightViewer}
              />
            </section>}
          </div>
        </main>
        <DetailsPanel
          networkPanel={(
            <NetworkPanel
              options={network}
              onChange={setNetwork}
              scenario={scenarioId}
              scenarioLabel={scenario.label}
              info={networkInfo}
              comparison={comparing ? {
                scenario: rightScenarioId,
                scenarioLabel: rightScenario.label,
                info: rightNetworkInfo,
              } : undefined}
            />
          )}
          landUsePanel={(
            <LandUsePanel
              options={landUse}
              onChange={setLandUse}
              probe={landUseProbe}
              comparing={comparing}
            />
          )}
          environmentPanel={(
            <EnvironmentPanel
              options={environment}
              onChange={setEnvironment}
              info={environmentInfo}
              comparison={comparing ? rightEnvironmentInfo : undefined}
            />
          )}
          morphologyPanel={(
            <>
              <MorphologyPanel
                options={morphology}
                onChange={changeMorphology}
                scenario={scenarioId}
              />
            </>
          )}
          noise={noise}
          noiseInfo={noiseInfo}
          onNoiseChange={changeNoise}
          cbs={cbs}
          onCbsChange={setCbs}
          open={detailsOpen}
          mode={mode}
          scenarioLabel={scenario.label}
          imageryVisible={imageryVisible}
          imageryOpacity={imageryOpacity}
          onOpacityChange={setImageryOpacity}
          buildingStatus={buildingStatus}
          surfaceStatus={surfaceStatus}
          terrainStatus={terrainStatus}
          wind={wind}
          windInfo={windInfo}
          onWindChange={changeWind}
          comparison={comparing ? {
            scenarioLabel: rightScenario.label,
            buildingStatus: rightBuildingStatus,
            surfaceStatus: rightSurfaceStatus,
            terrainStatus: rightTerrainStatus,
            windInfo: rightWindInfo,
            noiseInfo: rightNoiseInfo,
          } : undefined}
        />
      </div>
    </div>
  );
}
