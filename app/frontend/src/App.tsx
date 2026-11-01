import { useState } from 'react';
import Header from './components/Header';
import LayerPanel from './components/LayerPanel';
import DetailsPanel from './components/DetailsPanel';
import CesiumScene from './scene/CesiumScene';
import { scenarios } from './project';
import type { Mode, ScenarioId } from './project';
import styles from './App.module.css';
import type { ModelStatus } from './scene/modelLayers';

export default function App() {
  const [mode, setMode] = useState<Mode>('Explore');
  const [scenarioId, setScenarioId] = useState<ScenarioId>('scenario_a');
  const [layersOpen, setLayersOpen] = useState(true);
  const [detailsOpen, setDetailsOpen] = useState(true);
  const [imageryVisible, setImageryVisible] = useState(true);
  const [imageryOpacity, setImageryOpacity] = useState(1);
  const [contextVisible, setContextVisible] = useState(true);
  const [scenarioVisible, setScenarioVisible] = useState(true);
  const [buildingStatus, setBuildingStatus] = useState<ModelStatus>({ context: 'Loading', scenario: 'Loading' });
  const scenario = scenarios.find((item) => item.id === scenarioId)!;

  return (
    <div className={styles.app}>
      <a className={styles.skipLink} href="#scene">Skip to map</a>
      <Header mode={mode} scenarioId={scenarioId} onModeChange={setMode} onScenarioChange={setScenarioId} />
      <div className={styles.workspace} data-layers-open={layersOpen} data-details-open={detailsOpen}>
        <LayerPanel open={layersOpen} imageryVisible={imageryVisible} onImageryChange={setImageryVisible}
          contextVisible={contextVisible} scenarioVisible={scenarioVisible}
          onContextChange={setContextVisible} onScenarioChange={setScenarioVisible} />
        <main id="scene" className={styles.scene} tabIndex={-1} aria-label="Merwehaven map">
          <CesiumScene scenarioLabel={scenario.label} scenarioId={scenarioId}
            imageryVisible={imageryVisible} imageryOpacity={imageryOpacity}
            contextVisible={contextVisible} scenarioVisible={scenarioVisible} onBuildingStatus={setBuildingStatus} />
          <div className={styles.panelControls}>
            <button aria-expanded={layersOpen} aria-controls="layer-panel" onClick={() => setLayersOpen((open) => !open)}>Layers</button>
            <button aria-expanded={detailsOpen} aria-controls="details-panel" onClick={() => setDetailsOpen((open) => !open)}>Details</button>
          </div>
        </main>
        <DetailsPanel open={detailsOpen} mode={mode} scenarioLabel={scenario.label}
          imageryVisible={imageryVisible} imageryOpacity={imageryOpacity} onOpacityChange={setImageryOpacity}
          buildingStatus={buildingStatus} />
      </div>
    </div>
  );
}
