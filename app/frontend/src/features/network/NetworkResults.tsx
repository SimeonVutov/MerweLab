import type { ScenarioId } from '../../project';
import { isNetworkPath, selectedNetworkVariant } from './types';
import type { NetworkEntry, NetworkFeature, NetworkManifest, NetworkOptions, NetworkSummary } from './types';
import styles from './NetworkPanel.module.css';

export const indicatorLabels = {
    access: 'Weighted walking access · m',
    detour: 'Detour ratio',
    wind: 'Wind exposure · relative',
    car: 'Car route · m',
    green_loss: 'Paths on green · m',
    cost: 'Construction cost · relative',
} as const;

interface Props {
    data: NetworkManifest;
    options: NetworkOptions;
    scenario: ScenarioId;
    scenarioLabel: string;
    comparison?: { scenario: ScenarioId; scenarioLabel: string };
}

export default function NetworkResults({ data, options, scenario, scenarioLabel, comparison }: Props) {
    const left = data.scenarios[scenario]?.[selectedNetworkVariant(options, 'left')];
    const right = comparison && data.scenarios[comparison.scenario]?.[selectedNetworkVariant(options, 'right')];

    return (
        <section aria-label="Network indicators">
            <h3>Network indicators</h3>
            <table className={styles.table}>
                <thead>
                    <tr>
                        <th>Indicator</th>
                        <th>{scenarioLabel}</th>
                        {comparison && <th>{comparison.scenarioLabel}</th>}
                    </tr>
                </thead>
                <tbody>
                    {Object.entries(indicatorLabels).map(([key, label]) => (
                        <tr key={key}>
                            <th scope="row">{label}</th>
                            <td>{indicatorValue(left?.summary, key)}</td>
                            {comparison && <td>{indicatorValue(right?.summary, key)}</td>}
                        </tr>
                    ))}
                    <tr>
                        <th scope="row">Objective score · relative</th>
                        <td>{left?.summary.score.toFixed(3) ?? '—'}</td>
                        {comparison && <td>{right?.summary.score.toFixed(3) ?? '—'}</td>}
                    </tr>
                    <tr>
                        <th scope="row">Estimated car trips / day</th>
                        <td>{left?.summary.carTripsPerDay.toLocaleString() ?? '—'}</td>
                        {comparison && <td>{right?.summary.carTripsPerDay.toLocaleString() ?? '—'}</td>}
                    </tr>
                    <tr>
                        <th scope="row">Bridge selected</th>
                        <td>{bridgeValue(left)}</td>
                        {comparison && <td>{bridgeValue(right)}</td>}
                    </tr>
                </tbody>
            </table>
            <p className={styles.note}>Compare cost and scores within a scenario. Wind assumes 240°.</p>
            {(!left || (comparison && !right)) && <p className={styles.note}>Current has accessibility statistics only; no optimized network.</p>}

            <details>
                <summary>Objective weights</summary>
                <table className={styles.table}>
                    <thead>
                        <tr>
                            <th>Indicator</th>
                            <th>{scenarioLabel}</th>
                            {comparison && <th>{comparison.scenarioLabel}</th>}
                        </tr>
                    </thead>
                    <tbody>
                        {Object.entries(indicatorLabels).map(([key, label]) => (
                            <tr key={key}>
                                <th scope="row">{label}</th>
                                <td>{weightValue(left?.summary, key)}</td>
                                {comparison && <td>{weightValue(right?.summary, key)}</td>}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </details>
            {left && <a className={styles.figureLink} href={left.figure} target="_blank" rel="noreferrer">{scenarioLabel} · analysis figure</a>}
            {right && <a className={styles.figureLink} href={right.figure} target="_blank" rel="noreferrer">{comparison?.scenarioLabel} · analysis figure</a>}
        </section>
    );
}

function indicatorValue(summary: NetworkSummary | undefined, key: string) {
    if (!summary) return '—';
    return summary.indicators[key as keyof typeof indicatorLabels].toFixed(key === 'detour' || key === 'wind' ? 2 : 1);
}

function weightValue(summary: NetworkSummary | undefined, key: string) {
    if (!summary) return '—';
    return `${Math.round(summary.weights[key as keyof typeof indicatorLabels] * 100)}%`;
}

function bridgeValue(entry: NetworkEntry | undefined) {
    if (!entry) return '—';
    return entry.summary.bridgeBuilt ? 'Yes' : 'No';
}

export function NetworkSelection({ selected, label }: { selected: NetworkFeature | null; label: string }) {
    if (!selected) return null;

    let title = 'Garage ramp';
    let values: [string, string][] = [];
    if (isNetworkPath(selected)) {
        const path = selected.properties;
        title = path.seg_id;
        values = [
            ['Use', path.use],
            ['Kind', path.kind],
            ['Length', `${path.length.toFixed(1)} m`],
            ['Wind · relative', path.wind.toFixed(1)],
            ['Assigned residents', path.residents_walking.toLocaleString()],
            ['Estimated car trips / day', path.car_trips_per_day.toLocaleString()],
        ];
    } else if (selected.properties.layer === 'entrance') {
        title = 'Entrance';
        values = [['Building', selected.properties.building_id ?? 'Unknown']];
    }

    return (
        <section className={styles.selection} aria-label={`Selected network feature ${label}`}>
            <h3>{label} · {title}</h3>
            <dl>
                {values.map(([name, value]) => (
                    <div key={name}><dt>{name}</dt><dd>{value}</dd></div>
                ))}
            </dl>
        </section>
    );
}
