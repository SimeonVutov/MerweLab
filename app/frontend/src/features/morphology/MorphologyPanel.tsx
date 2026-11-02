import styles from './MorphologyPanel.module.css';
import { useEffect, useState } from 'react';
import { loadMorphology, morphologyIndicators, selectMorphologyLayer } from './data';
import type { MorphologyData, MorphologyOptions } from './data';
import type { ScenarioId } from '../../project';

interface Props {
  options: MorphologyOptions;
  onChange: (value: MorphologyOptions) => void;
  scenario: ScenarioId;
}

export default function MorphologyPanel({ options, onChange, scenario }: Props) {
  const [data, setData] = useState<MorphologyData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!options.enabled) {
      return;
    }
    let active = true;
    void loadMorphology().then((value) => {
      if (active) {
        setData(value);
        setError(null);
      }
    }).catch((cause: unknown) => {
      if (active) {
        setError(cause instanceof Error ? cause.message : 'Morphology metadata unavailable');
      }
    });
    return () => {
      active = false;
    };
  }, [options.enabled]);

  if (!options.enabled) {
    return null;
  }

  const layer = data && selectMorphologyLayer(data, options.indicator, scenario);
  const legend = layer?.legend;

  return (
    <section className={styles.panel} aria-label="Morphological indicators">
      <h2>Urban morphology</h2>
      {error && <p role="alert">{error}</p>}
      <label>
        Indicator
        <select
          value={options.indicator}
          onChange={(event) => onChange({ ...options, indicator: event.target.value })}
        >
          {morphologyIndicators.map(([id, label]) => (
            <option key={id} value={id}>{label}</option>
          ))}
        </select>
      </label>
      <label>
        Map opacity <output>{Math.round(options.opacity * 100)}%</output>
        <input
          type="range"
          min="0"
          max="100"
          value={Math.round(options.opacity * 100)}
          onChange={(event) => onChange({ ...options, opacity: Number(event.target.value) / 100 })}
        />
      </label>
      <button onClick={() => onChange({ ...options, focusRequest: options.focusRequest + 1 })}>
        View full analysis area
      </button>
      {data && !layer && <p>This indicator is available for V1 and V2 only.</p>}
      {legend?.categories?.map((category, index) => (
        <p key={category}>
          <span style={{ display: 'inline-block', width: 18, height: 12, marginRight: 8, background: legend.colours?.[index] }} />
          {category}
        </p>
      ))}
      {legend?.limits && (
        <div>
          <div
            className={styles.gradient}
            style={{ background: `linear-gradient(to right, ${legend.gradient?.join(', ')})` }}
          />
          <p>Colour scale: {legend.limits[0]?.toFixed(3)} to {legend.limits[1]?.toFixed(3)}</p>
        </div>
      )}
      <p>Site surfaces are hidden when enabling these terrain maps. Buildings remain visible. Re-enable Site surfaces to view the design pavement, which can cover the map.</p>
      <p>Grey: missing observations. Outside the research boundary is transparent.</p>
      <p>Analysis uses 50 m cells; fine H/W uses 25 m open-space support. Image pixels do not increase analytical resolution.</p>
      <p>These are rendered maps. Exact cell values and numerical threshold filters require numerical exports.</p>
      <p>Risk is a relative screening index with within-scenario normalization. Priority change shows the vulnerability adjustment, not proposal improvement against Current.</p>
    </section>
  );
}
