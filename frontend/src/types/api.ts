export type DecimalValue = string;

export type AnalyticalWarning = {
  code: string;
  message: string;
};

export type ResponseMeta = {
  source_version: string | null;
  source_version_id: number | null;
  indicator?: string | null;
  period_mode?: string | null;
  unit?: string | null;
};

export type Coverage = {
  status: "AVAILABLE" | "PARTIAL" | "EMPTY" | string;
  year_from: number | null;
  year_to: number | null;
  record_count?: number | null;
};

export type AnalyticalEnvelope<T> = {
  data: T;
  meta: ResponseMeta;
  coverage: Coverage;
  warnings: AnalyticalWarning[];
  methodology: string[];
};

export type CropVariant = {
  id: number;
  source_code: string;
  disaggregation: string;
  scientific_name: string;
};

export type Crop = {
  id: number;
  base_code: string;
  name: string;
  cycle: string;
  group: string;
  subgroup: string;
  general_classification: string;
  variants: CropVariant[];
};

export type Period = {
  year: number;
  period_type: string;
  label: string;
  chronological_order: number;
};

export type Source = {
  id: number;
  name: string;
  publisher: string;
  version_label: string;
  sha256: string;
  coverage: { year_from: number; year_to: number };
  status: string;
};

export type Department = {
  code: string;
  name: string;
  is_active: boolean;
};

export type Municipality = {
  code: string;
  department_code: string;
  name: string;
  is_active: boolean;
};

export type Summary = {
  planted_area_ha: DecimalValue;
  harvested_area_ha: DecimalValue;
  production_t: DecimalValue;
  yield_t_ha: DecimalValue | null;
  record_count: number;
};

export type SeriesPoint = Summary & {
  year: number;
  period_type: string;
};

export type RankingItem = {
  rank: number;
  id: string | number;
  name: string;
  value: DecimalValue;
  record_count: number;
};
