import { useState } from 'react';
import Header from './components/Header';
import LayerPanel from './components/LayerPanel';
import DetailsPanel from './components/DetailsPanel';
import { scenarios } from './project';
import type { Mode, ScenarioId } from './project';
import styles from './App.module.css';

export default function App() {
  const [mode, setMode] = useState<Mode>('Explore');
  const [scenarioId, setScenarioId] = useState<ScenarioId>('scenario_a');
  const [layersOpen, setLayersOpen] = useState(true);
  const [detailsOpen, setDetailsOpen] = useState(true);
  const scenario = scenarios.find((item) => item.id === scenarioId)!;

  return (
    <div className={styles.app}>
      <a className={styles.skipLink} href="#scene">Skip to map</a>
      <Header mode={mode} scenarioId={scenarioId} onModeChange={setMode} onScenarioChange={setScenarioId} />
      <div className={styles.workspace} data-layers-open={layersOpen} data-details-open={detailsOpen}>
        <LayerPanel open={layersOpen} />
        <main id="scene" className={styles.scene} tabIndex={-1} aria-label="Merwehaven map">
          <div className={styles.panelControls}>
            <button aria-expanded={layersOpen} aria-controls="layer-panel" onClick={() => setLayersOpen((open) => !open)}>Layers</button>
            <button aria-expanded={detailsOpen} aria-controls="details-panel" onClick={() => setDetailsOpen((open) => !open)}>Details</button>
          </div>
        </main>
        <DetailsPanel open={detailsOpen} mode={mode} scenarioLabel={scenario.label} />
      </div>
    </div>
  );
}
