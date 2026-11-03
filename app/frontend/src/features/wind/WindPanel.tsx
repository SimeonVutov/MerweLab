import type { WindInfo, WindMetricInfo, WindOptions } from './types';
import styles from './WindPanel.module.css';

interface WindPanelProps {
  info: WindInfo;
  options: WindOptions;
  onChange: (options: WindOptions) => void;
  showSample?: boolean;
}

function ColourLegend({ metric }: { metric: WindMetricInfo }) {
  return (
    <>
      <div
        className={styles.legend}
        aria-label={`${metric.label}: ${metric.range[0]} to ${metric.range[1]} ${metric.units}`}
      >
        {Array.from({ length: 16 }, (_, index) => (
          <span
            key={index}
            style={{ backgroundColor: metric.colours[Math.round(index / 15 * 255)] }}
          />
        ))}
      </div>
      <div className={styles.limits}>
        <span>≤{metric.range[0]}</span>
        <span>≥{metric.range[1]}</span>
      </div>
      <p className={styles.note}>{metric.units}</p>
    </>
  );
}

export default function WindPanel({ info, options, onChange, showSample = true }: WindPanelProps) {
  if (info.status === 'Off') {
    return null;
  }

  const metric = info.metric;

  return (
    <section className={styles.panel} aria-label="Wind results">
      <h2>Wind</h2>
      <p className={styles.note}>From 240° · steady RANS<br />16 m/s at 60 m · maps at 1.5 m</p>
      {options.metric && (
        <p className={styles.note}>
          Values are sampled 1.5 m above CFD ground. The map is draped over the displayed terrain; gaps indicate missing CFD data.
        </p>
      )}
      {info.status === 'Loading' && <p role="status">Loading…</p>}
      {info.error && <p role="alert">{info.error}</p>}
      {metric && (
        <>
          <h3>{metric.label}</h3>
          <ColourLegend metric={metric} />
          <label htmlFor="wind-opacity">Map opacity <output>{Math.round(options.opacity * 100)}%</output></label>
          <input
            id="wind-opacity"
            type="range"
            min="0"
            max="100"
            value={Math.round(options.opacity * 100)}
            onChange={(event) => onChange({ ...options, opacity: Number(event.target.value) / 100 })}
          />
          {showSample && info.sample && (
            <p aria-live="polite">
              {info.sample.value === null ? 'No data at this location' : `${info.sample.value.toFixed(2)} ${metric.units}`}
              {info.sample.flagged && <small className={styles.warning}>Flagged extreme · not validated</small>}
              {!info.sample.flagged && info.sample.outsideRange && (
                <small className={styles.warning}>Outside the displayed colour range</small>
              )}
            </p>
          )}
          {showSample && !info.sample && (
            <p className={styles.note}>Select a location for its value.</p>
          )}
        </>
      )}
      {info.flowLegend && options.metric !== 'speed' && (
        <>
          <h3>Streamline speed</h3>
          <ColourLegend metric={info.flowLegend} />
        </>
      )}
      {options.arrows && <p className={styles.note}>Arrow length: 20 m represents 10 m/s horizontal speed.</p>}
      {options.streamlines_2d && <p className={styles.note}>2D paths follow horizontal flow at pedestrian height.</p>}
      {options.streamlines_3d && <p className={styles.note}>3D paths show steady mean flow.</p>}
      {info.flaggedSamples > 0 && <p className={styles.note}>Flagged extreme speeds occur in these results.</p>}
      <p className={styles.note}>Not live weather or annual comfort classes.</p>
    </section>
  );
}
