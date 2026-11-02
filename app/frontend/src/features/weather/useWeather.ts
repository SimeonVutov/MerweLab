import { useEffect, useState } from 'react';
import { fields } from './types';
import type { Observation, WeatherPage } from './types';

function decodeRows(page: WeatherPage): Observation[] {
  return page.rows.map((row) => {
    const observation = { time: Date.parse(String(row[0])) } as Observation;
    for (const field of fields) {
      const index = page.columns.indexOf(field.id);
      const value = row[index];
      observation[field.id] = typeof value === 'number' ? value : null;
    }
    return observation;
  });
}

export function useWeather() {
  const [observations, setObservations] = useState<Observation[]>([]);
  const [page, setPage] = useState<WeatherPage | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastFetched, setLastFetched] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let cursor: string | undefined;
    let accumulated: Observation[] = [];
    let refreshing = false;

    async function refresh() {
      if (refreshing || controller.signal.aborted) return;

      refreshing = true;
      clearTimeout(timer);
      let through: string | undefined;

      try {
        let more = true;
        while (more && !controller.signal.aborted) {
          const query = new URLSearchParams();
          if (cursor) query.set('after', cursor);
          if (through) query.set('through', through);

          const response = await fetch(`/api/weather/observations?${query}`, {
            signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15_000)]),
            cache: 'no-store',
          });
          if (!response.ok) {
            throw new Error('Weather server unavailable');
          }

          const next: WeatherPage = await response.json();
          const additions = decodeRows(next);
          if (!through) through = next.history.lastObservation;
          if (next.hasMore && additions.length === 0) {
            throw new Error('Weather server returned an empty page');
          }

          accumulated = accumulated.concat(additions);
          if (additions.length > 0) {
            cursor = new Date(additions[additions.length - 1]!.time).toISOString();
          }

          setPage(next);
          setConnected(true);
          setLastFetched(Date.now());
          more = next.hasMore;
        }

        setObservations(accumulated);
        setLoading(false);
      } catch {
        if (!controller.signal.aborted) {
          setConnected(false);
          setLoading(false);
          setObservations(accumulated);
        }
      } finally {
        refreshing = false;
        if (!controller.signal.aborted) {
          timer = setTimeout(refresh, 60_000);
        }
      }
    }

    function onVisibilityChange() {
      if (document.visibilityState === 'visible') void refresh();
    }

    document.addEventListener('visibilitychange', onVisibilityChange);
    void refresh();
    return () => {
      controller.abort();
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);

  return { observations, page, connected, loading, lastFetched };
}
