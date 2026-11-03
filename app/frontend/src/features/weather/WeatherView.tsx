import WeatherHistory from './WeatherHistory';
import WeatherForecast from './WeatherForecast';
import { timeLabel } from './history';
import { useWeather } from './useWeather';
import styles from './WeatherView.module.css';

interface Props {
  hidden: boolean;
}

export default function WeatherView({ hidden }: Props) {
  const { observations, page, connected, loading, lastFetched } = useWeather();
  const latest = observations[observations.length - 1]?.time;

  return (
    <main id="weather" className={styles.weather} hidden={hidden}>
      <div className={styles.heading}>
        <h1>Weather</h1>
        <div className={styles.connection} role="status">
          <span className={styles.dot} data-connected={connected} />
          <span>{connected ? 'Connected' : 'Disconnected'}</span>
          <span className={styles.muted}>
            {lastFetched ? `Fetched ${timeLabel(lastFetched, { dateStyle: 'medium', timeStyle: 'short' })} UTC` : 'Waiting for server'}
          </span>
        </div>
      </div>

      <WeatherHistory
        observations={observations}
        loading={loading}
        totalCount={page?.history.observationCount}
        downloading={page?.sync.checking ?? false}
      />
      <WeatherForecast page={page} latest={latest} />
    </main>
  );
}
