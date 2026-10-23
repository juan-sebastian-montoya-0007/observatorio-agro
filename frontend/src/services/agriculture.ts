import type {
  AnalyticalEnvelope,
  RankingItem,
  SeriesPoint,
  Summary,
} from "@/types/api";
import type { DashboardFilters, RankingDimension } from "@/types/filters";

import { getAnalyticalEnvelope } from "./http";

function addOptional(
  params: URLSearchParams,
  key: string,
  value: string | number | undefined,
): void {
  if (value !== undefined && value !== "") {
    params.set(key, String(value));
  }
}

function agricultureParams(
  filters: DashboardFilters,
  options: { historical?: boolean } = {},
): URLSearchParams {
  const params = new URLSearchParams({
    year_from: String(options.historical ? 2019 : filters.year),
    year_to: String(filters.year),
    period_mode: filters.periodMode,
    indicator: filters.indicator,
  });
  addOptional(params, "department", filters.department);
  addOptional(params, "municipality", filters.municipality);
  addOptional(params, "crop", filters.crop);
  addOptional(params, "crop_variant", filters.cropVariant);
  addOptional(params, "group", filters.group);
  addOptional(params, "subgroup", filters.subgroup);
  addOptional(params, "cycle", filters.cycle);
  addOptional(params, "physical_state", filters.physicalState);
  if (filters.periodMode === "SOURCE") {
    params.set("period_type", filters.periodType ?? "ANNUAL");
  }
  return params;
}

export function getSummary(
  filters: DashboardFilters,
  signal?: AbortSignal,
): Promise<AnalyticalEnvelope<Summary | null>> {
  return getAnalyticalEnvelope(
    "/api/v1/agriculture/summary",
    agricultureParams(filters),
    signal,
  );
}

export function getSeries(
  filters: DashboardFilters,
  signal?: AbortSignal,
): Promise<AnalyticalEnvelope<SeriesPoint[]>> {
  return getAnalyticalEnvelope(
    "/api/v1/agriculture/series",
    agricultureParams(filters, { historical: true }),
    signal,
  );
}

export function getRankings(
  filters: DashboardFilters,
  dimension: RankingDimension,
  limit = 10,
  signal?: AbortSignal,
): Promise<AnalyticalEnvelope<RankingItem[]>> {
  const params = agricultureParams(filters);
  params.set("dimension", dimension);
  params.set("limit", String(limit));
  return getAnalyticalEnvelope("/api/v1/agriculture/rankings", params, signal);
}
