import { useMemo, useState } from 'react';
import WeatherChart from './WeatherChart';
import { aggregate, graphRange, periods, periodStart, shiftPeriod } from './history';
import type { Observation, Period } from './types';
import styles from './WeatherView.module.css';

interface Props {
  observations: Observation[];
  loading: boolean;
  totalCount?: number;
  downloading: boolean;
}

export default function WeatherHistory({ observations, loading, totalCount, downloading }: Props) {
  const [period, setPeriod] = useState<Period>('all');
  const [selectedTime, setSelectedTime] = useState<number | null>(null);
  const first = observations[0]?.time;
  const latest = observations[observations.length - 1]?.time;
  // Once the user navigates, arriving observations must not change their view.
  const anchor = selectedTime ?? latest ?? Date.now();

  const range = useMemo(() => {
    if (observations.length === 0) return null;
    return graphRange(observations, period, anchor);
  }, [observations, period, anchor]);

  const graph = useMemo(() => {
    if (!range) return [];
    return aggregate(observations, range[0], range[1], period);
  }, [observations, range, period]);

  function changePeriod(value: Period) {
    setPeriod(value);
    setSelectedTime(anchor);
  }

  const previousDisabled = first === undefined || periodStart(anchor, period) <= first;
  const nextDisabled = latest === undefined || shiftPeriod(anchor, period, 1) > latest;

  return (
    <section className={styles.history} aria-labelledby="weather-history-title">
      <div className={styles.toolbar}>
        <h2 id="weather-history-title">Historical observations</h2>
        <div className={styles.periods} role="group" aria-label="Visible period">
          {periods.map((item) => (
            <button
              key={item.id}
              aria-pressed={period === item.id}
              onClick={() => changePeriod(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.navigation}>
        {period !== 'all' && (
          <>
            <button
              aria-label={`Previous ${period}`}
              disabled={previousDisabled}
              onClick={() => setSelectedTime(shiftPeriod(anchor, period, -1))}
            >
              ←
            </button>
            <label>
              <span className={styles.muted}>Go to </span>
              <input
                type="date"
                aria-label="Go to date"
                min={first === undefined ? undefined : new Date(first).toISOString().slice(0, 10)}
                max={latest === undefined ? undefined : new Date(latest).toISOString().slice(0, 10)}
                value={new Date(anchor).toISOString().slice(0, 10)}
                onChange={(event) => {
                  if (event.target.value) setSelectedTime(Date.parse(`${event.target.value}T00:00:00Z`));
                }}
              />
            </label>
            <button
              aria-label={`Next ${period}`}
              disabled={nextDisabled}
              onClick={() => setSelectedTime(shiftPeriod(anchor, period, 1))}
            >
              →
            </button>
            <button onClick={() => setSelectedTime(latest ?? null)}>Latest</button>
          </>
        )}
        <span className={styles.muted}>
          {resolutionLabel(period)} · Rotterdam Airport
        </span>
      </div>

      {range && (
        <WeatherChart
          observations={graph}
          start={range[0]}
          end={range[1]}
        />
      )}
      {!range && (
        <div className={styles.empty} role="status">
          {loading || downloading ? 'Loading station history…' : 'Weather history is unavailable. Retrying automatically.'}
        </div>
      )}
      {(loading || downloading) && range && (
        <p className={styles.muted} role="status">
          Updating history… {(totalCount ?? observations.length).toLocaleString()} observations available
        </p>
      )}
    </section>
  );
}

function resolutionLabel(period: Period) {
  if (period === 'all' || period === 'year') return 'Daily means / maximum gust';
  if (period === 'month') return 'Hourly means / maximum gust';
  return '10-minute observations';
}
