import type { SeriesPoint } from '@/types/api';
import type { Indicator } from '@/types/filters';

export function variation(before: number | null, after: number | null) {
  return before !== null && before > 0 && after !== null ? (after / before - 1) * 100 : null;
}

export function stability(points: SeriesPoint[], indicator: Indicator) {
  const changes = points.slice(1).flatMap((point, index) => {
    const previous = points[index];
    if (point.year !== previous.year + 1 || point[indicator] === null || previous[indicator] === null) return [];
    const value = variation(Number(previous[indicator]), Number(point[indicator]));
    return value === null ? [] : [value];
  });
  if (!changes.length) return { average: null, deviation: null, min: null, max: null, increases: 0, count: 0 };
  const average = changes.reduce((sum, value) => sum + value, 0) / changes.length;
  return { average, deviation: Math.sqrt(changes.reduce((sum, value) => sum + (value - average) ** 2, 0) / changes.length), min: Math.min(...changes), max: Math.max(...changes), increases: changes.filter(value => value > 0).length, count: changes.length };
}
