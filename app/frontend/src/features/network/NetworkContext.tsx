import { useState } from 'react';
import type { NetworkManifest } from './types';
import styles from './NetworkPanel.module.css';

const facilities: Record<string, string> = {
    supermarket: 'Supermarket', gp: 'GP practice', pharmacy: 'Pharmacy',
    day_care: 'Day care', school: 'School', park: 'Park',
    tram_bus_stop: 'Tram / bus', metro: 'Metro', train_station: 'Train station',
};

export function BaselineAccessibility({ data }: { data: NetworkManifest }) {
    return (
        <details>
            <summary>Current accessibility</summary>
            <table className={styles.table}>
                <thead>
                    <tr><th>Destination</th><th>Mean · m</th><th>Walk · min</th></tr>
                </thead>
                <tbody>
                    {data.baseline.accessibility.map((row) => (
                        <tr key={row.facility}>
                            <th scope="row">{facilities[row.facility] ?? row.facility}</th>
                            <td>{row.meanDistance.toFixed(0)}</td>
                            <td>{row.walkMinutes.toFixed(1)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {data.baseline.figures.map((figure) => (
                <a className={styles.figureLink} key={figure.url} href={figure.url} target="_blank" rel="noreferrer">
                    {figure.label}
                </a>
            ))}
        </details>
    );
}

export function NetworkSensitivity({ data }: { data: NetworkManifest }) {
    const [parameter, setParameter] = useState('cost_weight');
    const selected = data.sensitivity.find((item) => item.parameter === parameter);
    if (!selected) return null;

    return (
        <details>
            <summary>V1 sensitivity results</summary>
            <label className={styles.control}>
                Tested parameter
                <select value={parameter} onChange={(event) => setParameter(event.target.value)}>
                    <option value="cost_weight">Cost weight</option>
                    <option value="bridge_cost_factor">Bridge cost multiplier</option>
                </select>
            </label>
            <table className={styles.table}>
                <thead><tr><th>Value</th><th>Bridge</th><th>Access · m</th></tr></thead>
                <tbody>
                    {selected.rows.map((row) => (
                        <tr key={row.value}>
                            <th scope="row">{row.value}</th>
                            <td>{row.bridgeBuilt ? 'Built' : 'Not built'}</td>
                            <td>{row.indicators.access?.toFixed(0)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </details>
    );
}
