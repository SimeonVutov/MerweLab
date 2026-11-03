import { useMemo, useState } from 'react';
import { fields } from './types';
import type { Field, Observation } from './types';
import { timeLabel } from './history';
import styles from './WeatherView.module.css';

interface Props {
    observations: Observation[];
    start: number;
    end: number;
}

function valueRange(observations: Observation[], field: Field): [number, number] {
    const values = observations.map((row) => row[field]).filter((value) => value !== null);
    if (values.length === 0) return [0, 1];

    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    if (minimum === maximum) return [minimum - 0.5, maximum + 0.5];
    return [minimum, maximum];
}

function linePath(observations: Observation[], field: Field, start: number, end: number) {
    // Different physical units share this plot, so each series uses its own
    // labelled range. A null starts a new path rather than bridging a data gap.
    const [minimum, maximum] = valueRange(observations, field);
    let drawing = false;
    const segments: string[] = [];

    for (const row of observations) {
        const value = row[field];
        if (value === null) {
            drawing = false;
            continue;
        }

        const x = 20 + (row.time - start) / (end - start) * 1160;
        const y = 265 - (value - minimum) / (maximum - minimum) * 240;
        segments.push(`${drawing ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`);
        drawing = true;
    }

    return segments.join(' ');
}

function isolatedPoints(observations: Observation[], field: Field, start: number, end: number) {
    const [minimum, maximum] = valueRange(observations, field);
    const points: { x: number; y: number }[] = [];

    for (const [index, row] of observations.entries()) {
        const value = row[field];
        if (value === null) continue;

        const previous = observations[index - 1]?.[field];
        const next = observations[index + 1]?.[field];
        if (typeof previous === 'number' || typeof next === 'number') continue;

        // An isolated observation has no line segment, so draw a dot for it.
        points.push({
            x: 20 + (row.time - start) / (end - start) * 1160,
            y: 265 - (value - minimum) / (maximum - minimum) * 240,
        });
    }

    return points;
}

export default function WeatherChart({ observations, start, end }: Props) {
    const [hidden, setHidden] = useState<Field[]>([]);
    const [hoveredTime, setHoveredTime] = useState<number | null>(null);
    const paths = useMemo(() => fields.map((field) => ({
        ...field,
        path: linePath(observations, field.id, start, end),
        points: isolatedPoints(observations, field.id, start, end),
        range: valueRange(observations, field.id),
    })), [observations, start, end]);

    const hovered = useMemo(() => {
        if (hoveredTime === null || observations.length === 0) return null;
        return observations.reduce((closest, row) => {
            if (Math.abs(row.time - hoveredTime) < Math.abs(closest.time - hoveredTime)) return row;
            return closest;
        });
    }, [observations, hoveredTime]);

    function toggle(field: Field) {
        setHidden((current) => {
            if (current.includes(field)) return current.filter((item) => item !== field);
            return [...current, field];
        });
    }

    return (
        <>
            <div className={styles.legend} aria-label="Chart series">
                {paths.map((field) => (
                    <button
                        key={field.id}
                        aria-pressed={!hidden.includes(field.id)}
                        className={styles.legendItem}
                        onClick={() => toggle(field.id)}
                    >
                        <span className={styles.swatch} style={{ background: field.color }} />
                        <span>{field.label}</span>
                        <span className={styles.muted}>
                            {hovered ? formatValue(hovered[field.id]) : `${field.range[0].toFixed(1)}–${field.range[1].toFixed(1)}`} {field.unit}
                        </span>
                    </button>
                ))}
            </div>
            <div className={styles.chart}>
                <svg
                    viewBox="0 0 1200 300"
                    preserveAspectRatio="none"
                    role="img"
                    aria-label="Historical station observations. Each coloured series uses its own scale; missing intervals are gaps."
                    onPointerMove={(event) => {
                        const bounds = event.currentTarget.getBoundingClientRect();
                        const fraction = (event.clientX - bounds.left) / bounds.width;
                        setHoveredTime(start + Math.max(0, Math.min(1, (fraction * 1200 - 20) / 1160)) * (end - start));
                    }}
                    onPointerLeave={() => setHoveredTime(null)}
                >
                    {[25, 85, 145, 205, 265].map((y) => (
                        <line key={y} x1="20" x2="1180" y1={y} y2={y} className={styles.gridline} />
                    ))}
                    {paths.filter((field) => !hidden.includes(field.id)).map((field) => (
                        <g key={field.id}>
                            <path
                                d={field.path}
                                stroke={field.color}
                                fill="none"
                                strokeWidth="1.6"
                                vectorEffect="non-scaling-stroke"
                            />
                            {field.points.map((point) => (
                                <circle key={point.x} cx={point.x} cy={point.y} r="3" fill={field.color} />
                            ))}
                        </g>
                    ))}
                    {hovered && (
                        <line
                            x1={20 + (hovered.time - start) / (end - start) * 1160}
                            x2={20 + (hovered.time - start) / (end - start) * 1160}
                            y1="20"
                            y2="270"
                            className={styles.cursor}
                        />
                    )}
                </svg>
                <div className={styles.axis}>
                    {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
                        <span key={fraction}>
                            {timeLabel(start + fraction * (end - start), {
                                day: '2-digit', month: 'short',
                                ...(end - start <= 86_400_000 ? { hour: '2-digit', minute: '2-digit' } : { year: 'numeric' }),
                            })}
                        </span>
                    ))}
                </div>
            </div>
            <div className={styles.chartNote}>
                <span>Independent scales · UTC</span>
                <span>{hovered ? timeLabel(hovered.time, { dateStyle: 'medium', timeStyle: 'short' }) : '\u00a0'}</span>
            </div>
        </>
    );
}

function formatValue(value: number | null) {
    if (value === null) return 'No data';
    return value.toFixed(1);
}
