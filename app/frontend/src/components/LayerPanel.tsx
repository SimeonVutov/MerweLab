import { layerGroups } from '../project';
import styles from './LayerPanel.module.css';

interface LayerPanelProps {
  open: boolean;
  imageryVisible: boolean;
  onImageryChange: (visible: boolean) => void;
}

export default function LayerPanel({ open, imageryVisible, onImageryChange }: LayerPanelProps) {
  return (
    <aside id="layer-panel" className={styles.panel} hidden={!open} aria-label="Layers">
      <h2>Layers</h2>
      <p className={styles.note}>Project layers are not connected yet.</p>
      {layerGroups.map((group) => (
        <details key={group.label} open={['Models', 'Environment', 'Morphology'].includes(group.label)}>
          <summary>{group.label}</summary>
          {group.layers.map((layer) => (
            <label key={layer.id} className={layer.id === 'aerial' ? styles.layer : styles.unavailable}
              title={layer.id === 'aerial' ? undefined : 'Not connected yet'}>
              <input type="checkbox" disabled={layer.id !== 'aerial'} checked={layer.id === 'aerial' && imageryVisible}
                onChange={(event) => { if (layer.id === 'aerial') onImageryChange(event.target.checked); }} />
              {layer.label}
            </label>
          ))}
        </details>
      ))}
    </aside>
  );
}
