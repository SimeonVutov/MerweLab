import { useEffect, useState } from 'react';
import { cbsColour, cbsGroups, cbsMetrics, cbsNoDataColour, cbsRange, loadCbs } from './data';
import type { CbsData, CbsFeature, CbsMetric, CbsOptions } from './data';
import styles from './CbsPanel.module.css';

interface CbsPanelProps {
  options: CbsOptions;
  onChange: (options: CbsOptions) => void;
}

const summaryLabels: Record<string, string> = {
  study_area: 'Study area',
  surrounding: 'Surroundings',
  M4H: 'M4H',
  Rotterdam: 'Rotterdam',
  Schiedam: 'Schiedam',
};

function displayValue(value: unknown) {
  if (typeof value !== 'number') {
    return 'No data';
  }

  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function IndicatorRow({ feature, metric, data }: { feature: CbsFeature; metric: CbsMetric; data: CbsData }) {
  const value = feature.properties[metric.key];
  const range = cbsRange(data, metric.key);
  let maximum = range?.[1] ?? 1;
  if (metric.unit === '%') {
    maximum = 100;
  }

  return (
    <div className={styles.row}>
      <div>
        <span>{metric.label}</span>
        <span>{displayValue(value)} {metric.unit}</span>
      </div>
      {typeof value === 'number' && (
        <meter
          aria-label={metric.label}
          min={0}
          max={Math.max(maximum, value, 1)}
          value={value}
        />
      )}
    </div>
  );
}

function MapLegend({ range, metric }: { range: [number, number] | null; metric: CbsMetric }) {
  let intervals: { low: number; high: number }[] = [];
  if (range) {
    const width = (range[1] - range[0]) / 5;
    if (width === 0) {
      intervals = [{ low: range[0], high: range[1] }];
    } else {
      intervals = Array.from({ length: 5 }, (_, index) => ({
        low: range[0] + index * width,
        high: range[0] + (index + 1) * width,
      }));
    }
  }

  return (
    <div className={styles.legend} aria-label={`${metric.label} legend`}>
      {intervals.map(({ low, high }, index) => (
        <div key={index}>
          <span
            className={styles.swatch}
            style={{ backgroundColor: cbsColour((low + high) / 2, range) }}
          />
          <span>{displayValue(low)} – {displayValue(high)} {metric.unit}</span>
        </div>
      ))}
      <div>
        <span className={styles.swatch} style={{ backgroundColor: cbsNoDataColour }} />
        <span>No data</span>
      </div>
      <small>Five equal-width classes across the supplied neighbourhoods. Equal values share one colour.</small>
    </div>
  );
}

export default function CbsPanel({ options, onChange }: CbsPanelProps) {
  const [data, setData] = useState<CbsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!options.enabled) {
      return;
    }

    let active = true;
    setError(null);

    void loadCbs().then((prepared) => {
      if (active) {
        setData(prepared);
      }
    }).catch((cause: unknown) => {
      if (active) {
        const message = cause instanceof Error ? cause.message : 'CBS data could not load';
        setError(message);
      }
    });

    return () => {
      active = false;
    };
  }, [options.enabled, attempt]);

  if (!options.enabled) {
    return null;
  }

  const metric = cbsMetrics.find((item) => item.key === options.metric) ?? cbsMetrics[0]!;
  const selected = data?.neighbourhoods.features.find((feature) => feature.id === options.selected);
  const range = data ? cbsRange(data, metric.key) : null;
  const summary = data?.summary.find((row) => row.variable === metric.key);
  let year = 'Not supplied';
  if (data?.reference_year) {
    year = String(data.reference_year);
  }

  function retry() {
    setAttempt((current) => current + 1);
    onChange({ ...options });
  }

  return (
    <section className={styles.panel} aria-label="CBS analysis">
      <h2>CBS neighbourhoods</h2>
      <p className={styles.note}>Existing context · shared across scenarios</p>
      <button
        disabled={!data}
        onClick={() => onChange({ ...options, focusRequest: options.focusRequest + 1 })}
      >
        View full CBS area
      </button>
      {error && (
        <div role="alert">
          <p>{error}</p>
          <button onClick={retry}>Try again</button>
        </div>
      )}
      {!data && !error && <p role="status">Loading CBS data…</p>}

      <label>
        Map indicator
        <select
          value={options.metric}
          onChange={(event) => onChange({ ...options, metric: event.target.value })}
        >
          {cbsGroups.map((group) => (
            <optgroup key={group} label={group}>
              {cbsMetrics.filter((item) => item.group === group).map((item) => (
                <option key={item.key} value={item.key}>{item.label}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      {data && <MapLegend range={range} metric={metric} />}
      <label>
        Opacity <output>{Math.round(options.opacity * 100)}%</output>
        <input
          type="range"
          min="0"
          max="100"
          value={Math.round(options.opacity * 100)}
          onChange={(event) => onChange({ ...options, opacity: Number(event.target.value) / 100 })}
        />
      </label>
      <label>
        Neighbourhood
        <select
          value={options.selected ?? ''}
          onChange={(event) => onChange({ ...options, selected: event.target.value || null })}
        >
          <option value="">Select on map or here</option>
          {data?.neighbourhoods.features.map((feature) => (
            <option key={feature.id} value={feature.id}>{feature.properties.buurtnaam}</option>
          ))}
        </select>
      </label>

      {selected && data && (
        <>
          <h3>{selected.properties.buurtnaam}</h3>
          <small>{selected.id}</small>
          <p>
            <strong>{metric.label}: {displayValue(selected.properties[metric.key])} {metric.unit}</strong>
          </p>
          {cbsGroups.map((group) => (
            <details key={group} open={['Population', 'Age', 'Households'].includes(group)}>
              <summary>{group}</summary>
              {cbsMetrics.filter((item) => item.group === group).map((item) => (
                <IndicatorRow
                  key={item.key}
                  feature={selected}
                  metric={item}
                  data={data}
                />
              ))}
            </details>
          ))}
        </>
      )}
      {summary && (
        <details>
          <summary>Regional comparison · {metric.label}</summary>
          <table>
            <caption>{metric.label} ({metric.unit})</caption>
            <tbody>
              {Object.entries(summary).filter(([key]) => key !== 'variable').map(([key, value]) => (
                <tr key={key}>
                  <th scope="row">{summaryLabels[key] ?? key}</th>
                  <td>{displayValue(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <small>Supplied summary values; aggregation method and weighting are not documented.</small>
        </details>
      )}

      <p className={styles.note}>
        Source: supplied CBS export. {data?.neighbourhoods.features.length ?? 14} neighbourhoods.
        Reference year: {year}. These are neighbourhood figures, not peninsula population estimates.
        Percentages may not total 100 due to rounding.
        Facility distances are neighbourhood averages, not individual routes.
      </p>
    </section>
  );
}
