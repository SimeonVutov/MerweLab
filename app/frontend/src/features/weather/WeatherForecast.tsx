import { timeLabel } from './history';
import type { WeatherPage } from './types';
import styles from './WeatherView.module.css';

interface Props {
    page: WeatherPage | null;
    latest?: number;
}

export default function WeatherForecast({ page, latest }: Props) {
    const forecast = page?.forecast;

    return (
        <section className={styles.forecasts} aria-labelledby="weather-forecast-title">
            <div className={styles.toolbar}>
                <h2 id="weather-forecast-title">Temperature forecast</h2>
                <span className={styles.muted}>
                    {forecast?.basedOn ? `Based on ${timeLabel(Date.parse(forecast.basedOn), { dateStyle: 'medium', timeStyle: 'short' })} UTC` : 'Repository LSTM models'}
                </span>
            </div>
            <div className={styles.forecastRows}>
                {[10, 30, 60].map((minutes) => {
                    const prediction = forecast?.predictions?.find((item) => item.minutes === minutes);
                    return (
                        <div className={styles.forecastRow} key={minutes}>
                            <span>+{minutes} min</span>
                            <strong>{prediction ? `${prediction.temperature.toFixed(1)} °C` : '—'}</strong>
                            <span className={styles.muted}>
                                {prediction ? `${timeLabel(Date.parse(prediction.time), { dateStyle: 'medium', timeStyle: 'short' })} UTC` : 'Unavailable'}
                            </span>
                        </div>
    );
                    })}
                </div>
                {!forecast?.available && <p className={styles.muted}>{forecast?.reason ?? 'Waiting for forecast'}</p>}
                {latest !== undefined && (
                    <p className={styles.muted}>Latest observation: {timeLabel(latest, { dateStyle: 'medium', timeStyle: 'short' })} UTC</p>
                )}
                {page?.sync.error && <p className={styles.muted} role="status">{page.sync.error}</p>}
            </section>
    );
}
