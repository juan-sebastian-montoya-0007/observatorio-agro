export type PeriodMode = "SOURCE" | "AGRICULTURAL_YEAR";

export type Indicator =
  | "planted_area_ha"
  | "harvested_area_ha"
  | "production_t"
  | "yield_t_ha";

export type DashboardFilters = {
  department?: string;
  municipality?: string;
  crop?: number;
  cropVariant?: number;
  group?: string;
  subgroup?: string;
  cycle?: string;
  physicalState?: string;
  year: number;
  periodMode: PeriodMode;
  indicator: Indicator;
};

export type RankingDimension = "department" | "municipality" | "crop";
