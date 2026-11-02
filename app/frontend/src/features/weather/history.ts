import { fields } from './types';
import type { Observation, Period } from './types';

export const periods: { id: Period; label: string }[] = [
  { id: 'all', label: 'All data' },
  { id: 'year', label: 'Year' },
  { id: 'month', label: 'Month' },
  { id: 'day', label: 'Day' },
  { id: 'hour', label: 'Hour' },
];

export function periodStart(time: number, period: Period): number {
  const date = new Date(time);
  if (period === 'year') return Date.UTC(date.getUTCFullYear(), 0);
  if (period === 'month') return Date.UTC(date.getUTCFullYear(), date.getUTCMonth());
  if (period === 'day') return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), date.getUTCHours());
}

export function shiftPeriod(time: number, period: Period, amount: number): number {
  const date = new Date(periodStart(time, period));
  if (period === 'year') date.setUTCFullYear(date.getUTCFullYear() + amount);
  if (period === 'month') date.setUTCMonth(date.getUTCMonth() + amount);
  if (period === 'day') date.setUTCDate(date.getUTCDate() + amount);
  if (period === 'hour') date.setUTCHours(date.getUTCHours() + amount);
  return date.getTime();
}

export function graphRange(observations: Observation[], period: Period, anchor: number): [number, number] {
  if (period === 'all') {
    // The view calls this only after the initial archive has loaded.
    return [observations[0]!.time, observations[observations.length - 1]!.time + 600_000];
  }
  return [periodStart(anchor, period), shiftPeriod(anchor, period, 1)];
}

export function aggregate(observations: Observation[], start: number, end: number, period: Period) {
  let interval = 600_000;
  if (period === 'all' || period === 'year') interval = 86_400_000;
  if (period === 'month') interval = 3_600_000;

  const buckets = new Map<number, Observation[]>();
  for (const row of observations) {
    if (row.time < start || row.time >= end) continue;
    const key = Math.floor(row.time / interval) * interval;
    const bucket = buckets.get(key) ?? [];
    bucket.push(row);
    buckets.set(key, bucket);
  }

  const result: Observation[] = [];
  for (let time = Math.floor(start / interval) * interval; time < end; time += interval) {
    const bucket = buckets.get(time) ?? [];
    const row = { time } as Observation;
    for (const field of fields) {
      row[field.id] = aggregateField(bucket, field.id);
    }
    result.push(row);
  }
  return result;
}

function aggregateField(bucket: Observation[], field: typeof fields[number]['id']) {
  const values = bucket.map((row) => row[field]).filter((value) => value !== null);
  if (values.length === 0) return null;

  // Maximum wind is a peak measurement; averaging it would hide gusts.
  if (field === 'max_wind_speed') return Math.max(...values);
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function timeLabel(time: number, options: Intl.DateTimeFormatOptions = {}) {
  return new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', ...options }).format(time);
}
