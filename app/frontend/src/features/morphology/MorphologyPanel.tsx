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
      <p>Enable maps on the left. Each selected map has its own opacity. Layers later in this list draw on top.</p>
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
      <p>2D hides solid buildings and site surfaces. In 3D, disable Site surfaces if design pavement covers a terrain map. Map toggles preserve the camera.</p>
      <p>Grey: missing observations. Outside the research boundary is transparent.</p>
      <p>Analysis uses 50 m cells; fine H/W uses 25 m open-space support. Image pixels do not increase analytical resolution.</p>
      <p>These are rendered maps. Exact cell values and numerical threshold filters require numerical exports.</p>
      <p>Risk is a relative screening index with within-scenario normalization. Priority change shows the vulnerability adjustment, not proposal improvement against Current.</p>
    </section>
  );
}
