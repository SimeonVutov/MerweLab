import { useEffect, useState } from 'react';
import type { ScenarioId } from '../../project';
import { loadNetworkManifest } from './data';
import { intensityColours, networkColourModes, networkColours } from './appearance';
import { hasNetworkLayers, networkVariants } from './types';
import type { NetworkColour, NetworkInfo, NetworkManifest, NetworkOptions, NetworkVariant } from './types';
import NetworkResults, { NetworkSelection } from './NetworkResults';
import { BaselineAccessibility, NetworkSensitivity } from './NetworkContext';
import styles from './NetworkPanel.module.css';

interface Props {
  options: NetworkOptions;
  onChange: (value: NetworkOptions) => void;
  scenario: ScenarioId;
  scenarioLabel: string;
  info: NetworkInfo;
  comparison?: { scenario: ScenarioId; scenarioLabel: string; info: NetworkInfo };
}

export default function NetworkPanel({ options, onChange, scenario, scenarioLabel, info, comparison }: Props) {
  const [data, setData] = useState<NetworkManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const enabled = hasNetworkLayers(options);

  useEffect(() => {
    if (!enabled) return;

    let active = true;
    void loadNetworkManifest().then((value) => {
      if (!active) return;

      setData(value);
      setError(null);
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : 'Network metadata unavailable');
    });
    return () => {
      active = false;
    };
  }, [enabled]);

  if (!enabled) return null;

  const errors = Array.from(new Set([error, info.error, comparison?.info.error].filter(Boolean)));

  return (
    <section className={styles.panel} aria-label="Route optimization">
      <h2>Route optimization</h2>
      {errors.map((message) => <p role="alert" key={message}>{message}</p>)}
      <label className={styles.control}>
        {comparison ? `${scenarioLabel} · left alternative` : 'Alternative'}
        <select
          aria-label="Network alternative"
          value={options.variant}
          onChange={(event) => onChange({ ...options, variant: event.target.value as NetworkVariant })}
        >
          {networkVariants.map((variant) => <option key={variant.id} value={variant.id}>{variant.label}</option>)}
        </select>
      </label>
      {comparison && (
        <label className={styles.control}>
          {comparison.scenarioLabel} · right alternative
          <select
            aria-label="Right network alternative"
            value={options.rightVariant ?? ''}
            onChange={(event) => {
              const value = event.target.value;
              const rightVariant = value ? value as NetworkVariant : null;
              onChange({ ...options, rightVariant });
            }}
          >
            <option value="">Same as left</option>
            {networkVariants.map((variant) => <option key={variant.id} value={variant.id}>{variant.label}</option>)}
          </select>
        </label>
      )}
      <label className={styles.control}>
        Colour paths by
        <select
          value={options.colour}
          onChange={(event) => onChange({ ...options, colour: event.target.value as NetworkColour })}
        >
          {networkColourModes.map((mode) => <option key={mode.id} value={mode.id}>{mode.label}</option>)}
        </select>
      </label>
      <label className={styles.control}>
        Opacity <output>{Math.round(options.opacity * 100)}%</output>
        <input
          aria-label="Network opacity"
          type="range"
          min="0"
          max="100"
          value={Math.round(options.opacity * 100)}
          onChange={(event) => onChange({ ...options, opacity: Number(event.target.value) / 100 })}
        />
      </label>
      <button
        onClick={() => onChange({ ...options, focusRequest: options.focusRequest + 1 })}
      >
        View pier network
      </button>

      <NetworkLegend options={options} data={data} />
      <p className={styles.note}>Walking assignments and car trips are estimates.</p>
      {info.status === 'Loading' && <p role="status">Loading network…</p>}
      {data && (
        <>
          <NetworkResults
            data={data}
            options={options}
            scenario={scenario}
            scenarioLabel={scenarioLabel}
            comparison={comparison}
          />
          <NetworkSelection selected={info.selected} label={scenarioLabel} />
          {comparison && <NetworkSelection selected={comparison.info.selected} label={comparison.scenarioLabel} />}
          <BaselineAccessibility data={data} />
          <NetworkSensitivity data={data} />
        </>
      )}
    </section>
  );
}

function NetworkLegend({ options, data }: { options: NetworkOptions; data: NetworkManifest | null }) {
  const labels = [
    { show: options.paths && options.colour === 'use', colour: networkColours.walking, label: 'Walk + bike' },
    { show: options.paths && options.colour === 'use', colour: networkColours.cars, label: 'Car + walk' },
    { show: options.candidates, colour: networkColours.candidate, label: 'Unbuilt candidate · dashed' },
    { show: options.entrances, colour: networkColours.entrance, label: 'Building entrance' },
    { show: options.ramp, colour: networkColours.ramp, label: 'Garage ramp' },
  ];
  const range = data && options.colour !== 'use' ? data.ranges[options.colour] : null;

  return (
    <div className={styles.legend} aria-label="Network legend">
      {labels.filter((item) => item.show).map((item) => (
        <div key={item.label}>
          <span className={styles.swatch} style={{ background: item.colour }} />{item.label}
        </div>
      ))}
      {range && options.paths && (
        <div>
          <div className={styles.gradient} style={{ background: `linear-gradient(to right, ${intensityColours.join(',')})` }} />
          <div className={styles.range}><span>{range[0].toFixed(1)}</span><span>{range[1].toFixed(1)}</span></div>
        </div>
      )}
    </div>
  );
}
