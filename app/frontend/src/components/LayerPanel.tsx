import { layerGroups } from '../project';
import styles from './LayerPanel.module.css';

interface LayerPanelProps { open: boolean }

export default function LayerPanel({ open }: LayerPanelProps) {
  return (
    <aside id="layer-panel" className={styles.panel} hidden={!open} aria-label="Layers">
      <h2>Layers</h2>
      <p className={styles.note}>Project layers are not connected yet.</p>
      {layerGroups.map((group) => (
        <details key={group.label} open={['Models', 'Environment', 'Morphology'].includes(group.label)}>
          <summary>{group.label}</summary>
          {group.layers.map((layer) => (
            <label key={layer.id} className={styles.unavailable} title="Not connected yet">
              <input type="checkbox" disabled checked={false} />
              {layer.label}
            </label>
          ))}
        </details>
      ))}
    </aside>
  );
}
