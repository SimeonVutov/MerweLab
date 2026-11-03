import styles from './MorphologyPanel.module.css';
import { useEffect, useState } from 'react';
import { hasMorphologyLayers, loadMorphology, morphologyIndicators, selectMorphologyLayer } from './data';
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
        if (!hasMorphologyLayers(options)) {
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
    }, [options.layers]);

    if (!hasMorphologyLayers(options)) {
        return null;
    }

    const enabled = options.order.filter((id) => options.layers[id]?.enabled);
    const showsRisk = enabled.some((id) => (
        id.startsWith('factor5_')
        || (id.startsWith('factor6_') && id !== 'factor6_age_45plus_introduction')
    ));

    function moveLayer(id: string, offset: number) {
        const order = [...options.order];
        const index = order.indexOf(id);
        const adjacent = enabled[enabled.indexOf(id) + offset];
        if (!adjacent) {
            return;
        }
        const target = order.indexOf(adjacent);
        [order[index], order[target]] = [order[target]!, order[index]!];
        onChange({ ...options, order });
    }

    return (
        <section className={styles.panel} aria-label="Morphological indicators">
            <h2>Urban morphology</h2>
            {error && <p role="alert">{error}</p>}
            <p>Select maps on the left and adjust their opacity here. Lower entries draw on top.</p>
            <button onClick={() => onChange({ ...options, focusRequest: options.focusRequest + 1 })}>
                View full analysis area
            </button>
            {enabled.map((id) => {
                const layer = data && selectMorphologyLayer(data, id, scenario);
                const legend = layer?.legend;
                const label = morphologyIndicators.find(([key]) => key === id)?.[1] ?? id;
                return (
                    <section key={id} aria-label={label}>
                        <h3>{label}</h3>
                        <label>
                            Opacity <output>{Math.round(options.layers[id]!.opacity * 100)}%</output>
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={Math.round(options.layers[id]!.opacity * 100)}
                                onChange={(event) => onChange({
                                    ...options,
                                    layers: { ...options.layers, [id]: { ...options.layers[id]!, opacity: Number(event.target.value) / 100 } },
                                })}
                            />
                        </label>
                        <button onClick={() => moveLayer(id, -1)} disabled={enabled.indexOf(id) === 0}>Lower layer</button>
                        <button onClick={() => moveLayer(id, 1)} disabled={enabled.indexOf(id) === enabled.length - 1}>Raise layer</button>
                        {data && !layer && <p>Not supplied for Current; available for V1/V2.</p>}
                        {legend?.categories?.map((category, index) => (
                            <p key={category}>
                                <span style={{ display: 'inline-block', width: 18, height: 12, marginRight: 8, background: legend.colours?.[index] }} />
                                {category}
                            </p>
                        ))}
                        {legend?.limits && (
                            <div>
                                <div className={styles.gradient} style={{ background: `linear-gradient(to right, ${legend.gradient?.join(', ')})` }} />
                                <p>Colour scale: {legend.limits[0]?.toFixed(3)} to {legend.limits[1]?.toFixed(3)}</p>
                            </div>
                        )}
                    </section>
                );
            })}
            <p>Grey: no data. Outside the research boundary: transparent.</p>
            {showsRisk && (
                <p>
                    Risk scores are normalized within each scenario. Priority change reflects vulnerability
                    adjustment, not improvement over Current.
                </p>
            )}
            <details>
                <summary>Map notes</summary>
                <p>Analysis resolution: 50 m; fine H/W: 25 m open spaces. Finer image pixels add no analytical detail.</p>
                <p>Rendered colours show the results; exact cell values and threshold filters are unavailable.</p>
            </details>
        </section>
    );
}
