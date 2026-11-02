import styles from '../../components/DetailsPanel.module.css';
import type { EnvironmentInfo, EnvironmentOptions } from './types';

interface EnvironmentPanelProps {
  options: EnvironmentOptions;
  onChange: (options: EnvironmentOptions) => void;
  info: EnvironmentInfo;
  comparison?: EnvironmentInfo;
}

export default function EnvironmentPanel({ options, onChange, info, comparison }: EnvironmentPanelProps) {
  if (!options.trees && !options.elevation) {
    return null;
  }

  return (
    <section className={styles.block} aria-label="Environment layers">
      <h2>Environment layers</h2>
      <dl className={styles.values}>
        {options.trees && <div><dt>Trees</dt><dd>{info.trees}</dd></div>}
        {options.elevation && <div><dt>Elevation colours</dt><dd>{info.elevation}</dd></div>}
        {comparison && options.trees && <div><dt>Right · trees</dt><dd>{comparison.trees}</dd></div>}
        {comparison && options.elevation && <div><dt>Right · elevation</dt><dd>{comparison.elevation}</dd></div>}
      </dl>
      {info.error && <p role="alert">{info.error}</p>}
      {comparison?.error && <p role="alert">Right map: {comparison.error}</p>}
      {options.trees && (
        <p className={styles.note}>
          228 supplied OSM-derived tree locations. Illustrative crowns and trunks retain the source
          model dimensions; they are not measured tree sizes. 2D shows location markers.
          Coverage follows the supplied dataset, not a complete tree inventory.
        </p>
      )}
      {options.elevation && (
        <>
          <label htmlFor="elevation-opacity">
            Elevation opacity <output>{Math.round(options.elevationOpacity * 100)}%</output>
          </label>
          <input
            id="elevation-opacity"
            type="range"
            min="0"
            max="100"
            value={Math.round(options.elevationOpacity * 100)}
            onChange={(event) => onChange({ ...options, elevationOpacity: Number(event.target.value) / 100 })}
          />
          <p className={styles.note}>
            Supplied AHN elevation colour image, draped on the numerical terrain.
            No numerical colour legend was supplied. Colours do not provide exact height readings.
            Analytical maps appear above this context layer.
          </p>
        </>
      )}
    </section>
  );
}
