import { useEffect, useState } from 'react';
import { loadLandUse, sampleLandUse } from './data';
import type { LandUseData } from './data';
import { hasLandUseLayers, landUseMaps } from './types';
import type { LandUseLayerOptions, LandUseLocation, LandUseMapId, LandUseOptions, LandUseSample, LandUseTarget } from './types';
import styles from './LandUsePanel.module.css';

interface Props {
    options: LandUseOptions;
    onChange: (value: LandUseOptions) => void;
    probe: LandUseLocation | null;
    comparing: boolean;
}

export default function LandUsePanel({ options, onChange, probe, comparing }: Props) {
    const [data, setData] = useState<LandUseData | null>(null);
    const [sample, setSample] = useState<LandUseSample | null>(null);
    const [error, setError] = useState<string | null>(null);
    const enabled = hasLandUseLayers(options);

    useEffect(() => {
        if (!enabled) return;

        let active = true;
        void loadLandUse().then(async (value) => {
            if (!active) return;

            setData(value);
            setError(null);
            setSample(null);
            if (!probe) return;

            const result = await sampleLandUse(value, probe);
            if (active) setSample(result);
        }).catch((cause: unknown) => {
            if (active) setError(cause instanceof Error ? cause.message : 'Land-use information unavailable');
        });

        return () => {
            active = false;
        };
    }, [enabled, probe]);

    if (!enabled) return null;

    function changeLayer(id: LandUseMapId, changes: Partial<LandUseLayerOptions>) {
        onChange({
            ...options,
            layers: {
                ...options.layers,
                [id]: { ...options.layers[id], ...changes },
            },
        });
    }

    return (
        <section className={styles.panel} aria-label="Land-use details">
            <h2>Land use</h2>
            {error && <p role="alert">{error}</p>}
            <button
                onClick={() => onChange({ ...options, focusRequest: options.focusRequest + 1 })}
            >
                View land-use area
            </button>

            {landUseMaps.filter(({ id }) => options.layers[id].enabled).map(({ id, label }) => (
                <section key={id} className={styles.controls}>
                    <h3>{label}</h3>
                    <label>
                        Opacity <output>{Math.round(options.layers[id].opacity * 100)}%</output>
                        <input
                            aria-label={`${label} opacity`}
                            type="range"
                            min="0"
                            max="100"
                            value={Math.round(options.layers[id].opacity * 100)}
                            onChange={(event) => changeLayer(id, { opacity: Number(event.target.value) / 100 })}
                        />
                    </label>
                    {comparing && (
                        <label>
                            Show in
                            <select
                                aria-label={`${label} comparison pane`}
                                value={options.layers[id].target}
                                onChange={(event) => changeLayer(id, { target: event.target.value as LandUseTarget })}
                            >
                                <option value="both">Both maps</option>
                                <option value="left">Left map</option>
                                <option value="right">Right map</option>
                            </select>
                        </label>
                    )}
                </section>
            ))}

            {(options.layers.optimized.enabled || options.layers.changes.enabled) && (
                <p className={styles.note}>The optimized proposal is shared by V1 and V2.</p>
            )}
            {options.layers.changes.enabled && <p className={styles.note}>Changed-cell colours show the proposed class. Unchanged cells are transparent.</p>}
            {data && <LandUseAreas data={data} />}
            {data && sample && <CellDetails data={data} sample={sample} />}
        </section>
    );
}

function LandUseAreas({ data }: { data: LandUseData }) {
    const total = data.summary.areaSquareMetres;
    const changed = data.summary.changedAreaSquareMetres / total * 100;

    return (
        <section className={styles.areas} aria-label="Land-use area shares">
            <h3>Area share · full coverage</h3>
            <table>
                <thead>
                    <tr>
                        <th>Class</th>
                        <th>Existing</th>
                        <th>Optimized</th>
                    </tr>
                </thead>
                <tbody>
                    {data.classes.map((category) => {
                        const area = data.summary.classes.find((item) => item.code === category.code)!;
                        return (
                            <tr key={category.code}>
                                <th scope="row">
                                    <span className={styles.swatch} style={{ background: category.colour }} />
                                    {category.label}
                                </th>
                                <td>{(area.existingArea / total * 100).toFixed(1)}%</td>
                                <td>{(area.optimizedArea / total * 100).toFixed(1)}%</td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
            <p>{(total / 10000).toFixed(1)} ha covered · {changed.toFixed(1)}% changed</p>
        </section>
    );
}

function CellDetails({ data, sample }: { data: LandUseData; sample: LandUseSample }) {
    if (sample.outside) return <p>Selected point is outside the land-use coverage.</p>;
    if (sample.existing === null || sample.optimized === null) return <p>No land-use data at this point.</p>;

    const existing = data.classes.find((item) => item.code === sample.existing)!.label;
    const optimized = data.classes.find((item) => item.code === sample.optimized)!.label;

    return (
        <section className={styles.cell} aria-label="Selected land-use cell">
            <h3>Selected cell</h3>
            <dl>
                <div><dt>Existing</dt><dd>{existing}</dd></div>
                <div><dt>Optimized</dt><dd>{optimized}</dd></div>
                <div><dt>Changed</dt><dd>{sample.existing === sample.optimized ? 'No' : 'Yes'}</dd></div>
            </dl>
        </section>
    );
}
