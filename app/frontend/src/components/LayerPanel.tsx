import { layerGroups } from '../project';
import type { LayerId } from '../project';
import styles from './LayerPanel.module.css';
import type { WindOptions } from '../features/wind/types';

interface LayerPanelProps {
  open: boolean;
  imageryVisible: boolean;
  onImageryChange: (visible: boolean) => void;
  contextVisible: boolean;
  scenarioVisible: boolean;
  onContextChange: (visible: boolean) => void;
  onScenarioChange: (visible: boolean) => void;
  groundVisible: boolean;
  waterVisible: boolean;
  onGroundChange: (visible: boolean) => void;
  onWaterChange: (visible: boolean) => void;
  wind: WindOptions;
  onWindChange: (options: WindOptions) => void;
}

export default function LayerPanel({ open, imageryVisible, onImageryChange, contextVisible, scenarioVisible, onContextChange, onScenarioChange,
  groundVisible, waterVisible, onGroundChange, onWaterChange,
  wind, onWindChange,
}: LayerPanelProps) {
  const controls: Partial<Record<LayerId, { checked: boolean; change: (visible: boolean) => void }>> = {
    aerial: { checked: imageryVisible, change: onImageryChange },
    'context-buildings': { checked: contextVisible, change: onContextChange },
    'scenario-buildings': { checked: scenarioVisible, change: onScenarioChange },
    'site-surfaces': { checked: groundVisible, change: onGroundChange },
    water: { checked: waterVisible, change: onWaterChange },
    'wind-speed': { checked: wind.metric === 'speed', change: (checked) => onWindChange({ ...wind, metric: checked ? 'speed' : null }) },
    turbulence: { checked: wind.metric === 'turbulence', change: (checked) => onWindChange({ ...wind, metric: checked ? 'turbulence' : null }) },
    'wind-pressure': { checked: wind.metric === 'pressure', change: (checked) => onWindChange({ ...wind, metric: checked ? 'pressure' : null }) },
    'wind-arrows': { checked: wind.arrows, change: (checked) => onWindChange({ ...wind, arrows: checked }) },
    'streamlines-2d': { checked: wind.streamlines_2d, change: (checked) => onWindChange({ ...wind, streamlines_2d: checked }) },
    'streamlines-3d': { checked: wind.streamlines_3d, change: (checked) => onWindChange({ ...wind, streamlines_3d: checked }) },
  };
  return (
    <aside id="layer-panel" className={styles.panel} hidden={!open} aria-label="Layers">
      <h2>Layers</h2>
      <p className={styles.note}>Greyed layers are not connected yet.</p>
      {layerGroups.map((group) => (
        <details key={group.label} open={['Models', 'Environment', 'Morphology'].includes(group.label)}>
          <summary>{group.label}</summary>
          {group.layers.map((layer) => {
            const control = controls[layer.id];
            return <label key={layer.id} className={control ? styles.layer : styles.unavailable}
              title={control ? undefined : 'Not connected yet'}>
              <input type="checkbox" disabled={!control} checked={control?.checked ?? false}
                onChange={(event) => control?.change(event.target.checked)} />
              {layer.label}
            </label>;
          })}
        </details>
      ))}
    </aside>
  );
}
