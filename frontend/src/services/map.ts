import type { AnalyticalEnvelope } from "@/types/api";
import type { DashboardFilters } from "@/types/filters";

import { getAnalyticalEnvelope } from "./http";

export type MapPosition = [number, number];
export type MapGeometry =
  | { type: "Polygon"; coordinates: MapPosition[][] }
  | { type: "MultiPolygon"; coordinates: MapPosition[][][] };

export type MapFeature = {
  type: "Feature";
  geometry: MapGeometry;
  properties: {
    code: string;
    name: string;
    department_code: string;
    value: number | null;
    record_count: number;
  };
};

export type TerritorialMapData = {
  level: "department" | "municipality";
  geojson: { type: "FeatureCollection"; features: MapFeature[] };
  source: { name: string; publisher: string; url: string; retrieved_at: string; sha256: string };
  unmatched_codes: string[];
};

export function getTerritorialMap(
  filters: DashboardFilters,
  signal?: AbortSignal,
): Promise<AnalyticalEnvelope<TerritorialMapData>> {
  const params = new URLSearchParams({
    year_from: String(filters.yearFrom ?? filters.year),
    year_to: String(filters.year),
    period_mode: filters.periodMode,
    indicator: filters.indicator,
  });
  for (const [key, value] of Object.entries({
    department: filters.department,
    municipality: filters.municipality,
    crop: filters.crop,
    crop_variant: filters.cropVariant,
    group: filters.group,
    subgroup: filters.subgroup,
    cycle: filters.cycle,
    classification: filters.classification,
    physical_state: filters.physicalState,
    period_type: filters.periodMode === "SOURCE" ? filters.periodType ?? "ANNUAL" : undefined,
  })) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  return getAnalyticalEnvelope("/api/v1/geography/map", params, signal);
}
