import type { Mode } from '../project';
import styles from './DetailsPanel.module.css';
import type { ModelStatus } from '../scene/modelLayers';
import type { TerrainStatus } from '../scene/terrain';

interface DetailsPanelProps {
  open: boolean;
  mode: Mode;
  scenarioLabel: string;
  imageryVisible: boolean;
  imageryOpacity: number;
  onOpacityChange: (opacity: number) => void;
  buildingStatus: ModelStatus;
  surfaceStatus: ModelStatus;
  terrainStatus: TerrainStatus;
}

export default function DetailsPanel({ open, mode, scenarioLabel, imageryVisible, imageryOpacity, onOpacityChange, buildingStatus,
  surfaceStatus, terrainStatus,
}: DetailsPanelProps) {
  return (
    <aside id="details-panel" className={styles.panel} hidden={!open} aria-label="Details">
      <div>
        <h2>{mode === 'Explore' ? scenarioLabel : mode}</h2>
        {mode === 'Explore' && <>
          <dl className={styles.values}>
            <div><dt>Scenario</dt><dd>{scenarioLabel}</dd></div>
            <div><dt>Context buildings</dt><dd>{buildingStatus.context}</dd></div>
            <div><dt>Scenario buildings</dt><dd>{buildingStatus.scenario}</dd></div>
            <div><dt>AHN terrain</dt><dd>{terrainStatus}</dd></div>
            <div><dt>Site surfaces</dt><dd>{surfaceStatus.scenario}</dd></div>
            <div><dt>Water</dt><dd>{surfaceStatus.water}</dd></div>
          </dl>
          <section className={styles.block}>
            <h2>Aerial imagery</h2>
            <p className={styles.note}>PDOK · latest 25 cm imagery</p>
            <label htmlFor="imagery-opacity">Opacity <output>{Math.round(imageryOpacity * 100)}%</output></label>
            <input id="imagery-opacity" type="range" min="0" max="100" value={Math.round(imageryOpacity * 100)}
              disabled={!imageryVisible} onChange={(event) => onOpacityChange(Number(event.target.value) / 100)} />
          </section>
        </>}
        {mode === 'Compare' && <p className={styles.note}>Comparison will be connected in a later update.</p>}
        {mode === 'Weather' && <p className={styles.note}>Weather visualization to be agreed.</p>}
      </div>
    </aside>
  );
}
