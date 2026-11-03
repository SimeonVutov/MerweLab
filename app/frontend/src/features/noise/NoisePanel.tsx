import { useEffect, useState } from 'react';
import { loadNoiseManifest } from './data';
import type { NoiseManifest } from './data';
import { noisePeriods } from './types';
import type { NoiseInfo, NoiseOptions } from './types';
import styles from './NoisePanel.module.css';

interface NoisePanelProps {
  options: NoiseOptions;
  onChange: (options: NoiseOptions) => void;
  info: NoiseInfo;
  scenarioLabel: string;
  comparison?: { scenarioLabel: string; info: NoiseInfo };
}

function NoiseReadout({ info, label, options }: { info: NoiseInfo; label: string; options: NoiseOptions }) {
  const sample = info.sample;
  let belowThreshold = false;
  if (sample?.band && options.thresholdEnabled && sample.band.upper !== null) {
    belowThreshold = sample.band.upper <= options.threshold;
  }

  return (
    <section className={styles.readout} aria-label={`${label} noise results`}>
      <h3>{label}</h3>
      <p role="status">Noise map: {info.status}</p>
      {info.error && <p role="alert">{info.error}</p>}
      {sample && (
        <>
          <p>
            Contour band: <strong>{sample.band?.label ?? 'No data'}</strong>
            {sample.band && ' dB(A)'}
          </p>
          {belowThreshold && <p className={styles.note}>Below the active threshold; hidden on the map.</p>}
          {sample.receiver && (
            <p>
              Nearest receiver ({sample.receiver.distanceM} m away):{' '}
              <strong>{sample.receiver.value?.toFixed(2) ?? 'No data'}</strong> dB(A)
              <small>Receiver {sample.receiver.id}; this is a separate calculated point.</small>
            </p>
          )}
          {sample.receiverStatus === 'Loading' && <p role="status">Loading trusted receiver values…</p>}
          {sample.receiverStatus === 'Loaded' && !sample.receiver && (
            <p className={styles.note}>No calculated receiver within 75 m.</p>
          )}
          {sample.receiverStatus === 'Unavailable for V1' && (
            <p className={styles.note}>V1 receiver values are excluded. Only the exported contour band is shown.</p>
          )}
          {sample.receiverStatus === 'Unavailable' && (
            <p className={styles.note}>Receiver values could not load. The contour band remains available.</p>
          )}
        </>
      )}
    </section>
  );
}

export default function NoisePanel({ options, onChange, info, scenarioLabel, comparison }: NoisePanelProps) {
  const [data, setData] = useState<NoiseManifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!options.enabled) {
      return;
    }

    let active = true;
    setError(null);
    void loadNoiseManifest().then((manifest) => {
      if (active) {
        setData(manifest);
      }
    }).catch((cause: unknown) => {
      if (active) {
        const message = cause instanceof Error ? cause.message : 'Noise metadata could not load';
        setError(message);
      }
    });

    return () => {
      active = false;
    };
  }, [options.enabled, options.retryRequest]);

  if (!options.enabled) {
    return null;
  }

  const hasError = error || info.error || comparison?.info.error;

  return (
    <section className={styles.panel} aria-label="Noise analysis">
      <h2>Road-traffic noise</h2>
      {error && <p role="alert">{error}</p>}
      {hasError && (
        <button onClick={() => onChange({ ...options, retryRequest: options.retryRequest + 1 })}>
          Retry noise loading
        </button>
      )}
      <label>
        Noise period
        <select
          value={options.period}
          onChange={(event) => onChange({ ...options, period: event.target.value as NoiseOptions['period'] })}
        >
          {noisePeriods.map((period) => (
            <option key={period.id} value={period.id}>{period.label}</option>
          ))}
        </select>
      </label>
      <label className={styles.checkbox}>
        <input
          type="checkbox"
          checked={options.thresholdEnabled}
          onChange={(event) => onChange({ ...options, thresholdEnabled: event.target.checked })}
        />
        Show only levels at or above the threshold
      </label>
      <label>
        Noise threshold <output>{options.threshold} dB(A)</output>
        <input
          type="range"
          min="35"
          max="80"
          step="5"
          disabled={!options.thresholdEnabled}
          value={options.threshold}
          onChange={(event) => onChange({ ...options, threshold: Number(event.target.value) })}
        />
      </label>
      <p className={styles.note}>5 dB bands; filtering uses the same steps.</p>
      <label>
        Noise opacity <output>{Math.round(options.opacity * 100)}%</output>
        <input
          type="range"
          min="0"
          max="100"
          value={Math.round(options.opacity * 100)}
          onChange={(event) => onChange({ ...options, opacity: Number(event.target.value) / 100 })}
        />
      </label>

      {data && (
        <div className={styles.legend} aria-label="Noise band legend">
          {data.classes.map((band) => {
            let hidden = false;
            if (options.thresholdEnabled && band.upper !== null) {
              hidden = band.upper <= options.threshold;
            }

            return (
              <div key={band.code} className={hidden ? styles.filtered : undefined}>
                <span className={styles.swatch} style={{ backgroundColor: band.colour }} />
                <span>{band.label} dB(A)</span>
              </div>
            );
          })}
          <small>Missing coverage is transparent; it is not zero noise.</small>
        </div>
      )}
      <p className={styles.note}>
        Select a location to inspect its band. Compare uses the same location and scale.
      </p>
      <NoiseReadout info={info} label={scenarioLabel} options={options} />
      {comparison && (
        <NoiseReadout info={comparison.info} label={comparison.scenarioLabel} options={options} />
      )}
      <details>
        <summary>Model notes</summary>
        <p className={styles.note}>
          Calculated at 1.5 m above ground. Bands are ranges, not exact point values.
          Lden includes evening and night weighting.
        </p>
      </details>
    </section>
  );
}
