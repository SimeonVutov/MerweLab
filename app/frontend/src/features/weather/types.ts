export const fields = [
    { id: 'temperature', label: 'Temperature', unit: '°C', color: '#c86e4c' },
    { id: 'humidity', label: 'Humidity', unit: '%', color: '#598ac7' },
    { id: 'pressure', label: 'Pressure', unit: 'hPa', color: '#a38acb' },
    { id: 'average_wind_speed', label: 'Wind speed', unit: 'm/s', color: '#449c82' },
    { id: 'max_wind_speed', label: 'Maximum wind', unit: 'm/s', color: '#b49a38' },
] as const;

export type Field = typeof fields[number]['id'];
export type Observation = { time: number } & Record<Field, number | null>;
export type Period = 'all' | 'year' | 'month' | 'day' | 'hour';

export interface Forecast {
    available: boolean;
    reason?: string;
    basedOn?: string;
    predictions?: { minutes: number; time: string; temperature: number; testRmse: number }[];
}

export interface WeatherPage {
    columns: string[];
    rows: (string | number | null)[][];
    hasMore: boolean;
    history: { start: string | null; lastObservation: string | null; observationCount: number };
    sync: {
        enabled: boolean;
        checking: boolean;
        lastChecked: string | null;
        lastSuccessfulCheck: string | null;
        error: string | null;
        downloadedThrough: string | null;
    };
    forecast: Forecast;
}
