import { useEffect, useState } from 'react';
import type { Viewer } from 'cesium';
import CompareToolbar from './features/compare/CompareToolbar';
import { synchronizeCameras } from './features/compare/synchronizeCameras';
import { initialCbsOptions } from './features/cbs/data';
import type { CbsOptions } from './features/cbs/data';
import { initialNoiseInfo, initialNoiseOptions } from './features/noise/types';
import type { NoiseInfo, NoiseLocation, NoiseOptions } from './features/noise/types';
import MorphologyPanel from './features/morphology/MorphologyPanel';
import { hasMorphologyLayers, initialMorphologyOptions } from './features/morphology/data';
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
  const [mode, setMode] = useState<Mode>('Explore');
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
    morphology,
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

  function selectNeighbourhood(id: string) {
    setCbs((current) => ({ ...current, selected: id }));
    setDetailsOpen(true);
  }

  function changeCbs(options: CbsOptions) {
    setCbs(options);
    if (options.enabled) {
      setDetailsOpen(true);
    }
  }

  function changeMorphology(options: typeof morphology) {
    setMorphology(options);
    if (hasMorphologyLayers(options)) {
      if (!hasMorphologyLayers(morphology)) {
        // Site meshes cover globe imagery and mask the terrain beneath the proposal.
        setGroundVisible(false);
      }
      setDetailsOpen(true);
    }
  }

  function changeNoise(options: NoiseOptions) {
    setNoise(options);
    if (options.enabled) {
      setDetailsOpen(true);
    }
  }

  function changeWind(options: WindOptions) {
    setWind(options);
  }

  useEffect(() => {
    if (!comparing || !leftViewer || !rightViewer || leftViewer.isDestroyed() || rightViewer.isDestroyed()) {
      return;
    }

    return synchronizeCameras(leftViewer, rightViewer);
  }, [comparing, leftViewer, rightViewer]);

  return (
    <div className={styles.app}>
      <a className={styles.skipLink} href="#scene">Skip to map</a>
      <Header
        mode={mode}
        scenarioId={scenarioId}
        onModeChange={setMode}
        onScenarioChange={setScenarioId}
      />
      <div
        className={styles.workspace}
        data-layers-open={layersOpen}
        data-details-open={detailsOpen}
      >
        <LayerPanel
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
                onBuildingStatus={setBuildingStatus}
                onSurfaceStatus={setSurfaceStatus}
                onTerrainStatus={setTerrainStatus}
                onWindInfo={setWindInfo}
                onNoiseInfo={setNoiseInfo}
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
                scenarioLabel={rightScenario.label}
                scenarioId={rightScenarioId}
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
