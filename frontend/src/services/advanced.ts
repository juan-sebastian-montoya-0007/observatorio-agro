import type { DashboardFilters, Indicator } from '@/types/filters';
import type { SeriesPoint, Summary } from '@/types/api';
import { getAnalyticalEnvelope } from './http';

export type Query = DashboardFilters & { yearFrom: number; dimension: 'municipality' | 'department' | 'year' | 'crop'; orderBy: Indicator; direction: 'asc' | 'desc'; limit: number; compareYear: number; compare: boolean; secondary: Indicator | ''; showVariation: boolean };
export type QueryRow = Record<Indicator, number | null> & { id: string; name: string; department: string; variation: number | null };
export type QueryResult = { rows: QueryRow[]; total: number; summary: Summary | null; national_summary: Summary | null; municipalities: QueryRow[]; series: SeriesPoint[]; national_series: SeriesPoint[]; top_yield: QueryRow[]; composition: QueryRow[]; increases: number; decreases: number };
export function runQuery(query: Query, signal?: AbortSignal) {
  const params = new URLSearchParams({ year_from: String(query.yearFrom), year_to: String(query.year), period_mode: query.periodMode, indicator: query.indicator, dimension: query.dimension, order_by: query.orderBy, direction: query.direction, limit: String(query.limit), compare_year: String(query.compareYear) });
  for (const [key, value] of Object.entries({ department: query.department, municipality: query.municipality, crop: query.crop, crop_variant: query.cropVariant, physical_state: query.physicalState, group: query.group, subgroup: query.subgroup, cycle: query.cycle, classification: query.classification, period_type: query.periodMode === 'SOURCE' ? query.periodType ?? 'ANNUAL' : undefined })) {
    if (value !== undefined && value !== '') params.set(key, String(value));
  }
  return getAnalyticalEnvelope<QueryResult>('/api/v1/agriculture/advanced', params, signal);
}
