import type { Mode } from '../project';
import styles from './DetailsPanel.module.css';

interface DetailsPanelProps {
  open: boolean;
  mode: Mode;
  scenarioLabel: string;
}

export default function DetailsPanel({ open, mode, scenarioLabel }: DetailsPanelProps) {
  return (
    <aside id="details-panel" className={styles.panel} hidden={!open} aria-label="Details">
      <div>
        <h2>{mode === 'Explore' ? scenarioLabel : mode}</h2>
        {mode === 'Explore' && <p className={styles.note}>Project layers are not connected yet.</p>}
        {mode === 'Compare' && <p className={styles.note}>Comparison will be connected in a later update.</p>}
        {mode === 'Weather' && <p className={styles.note}>Weather visualization to be agreed.</p>}
      </div>
    </aside>
  );
}
