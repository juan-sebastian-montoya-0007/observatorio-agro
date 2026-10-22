import type {
  AnalyticalEnvelope,
  Crop,
  Department,
  Municipality,
  Period,
  Source,
} from "@/types/api";

import { getAnalyticalEnvelope } from "./http";

export type Catalogs = {
  crops: AnalyticalEnvelope<Crop[]>;
  periods: AnalyticalEnvelope<Period[]>;
  sources: AnalyticalEnvelope<Source[]>;
};

export async function getCatalogs(signal?: AbortSignal): Promise<Catalogs> {
  const [crops, periods, sources] = await Promise.all([
    getAnalyticalEnvelope<Crop[]>("/api/v1/catalog/crops", undefined, signal),
    getAnalyticalEnvelope<Period[]>("/api/v1/catalog/periods", undefined, signal),
    getAnalyticalEnvelope<Source[]>("/api/v1/catalog/sources", undefined, signal),
  ]);
  return { crops, periods, sources };
}

export function getDepartments(
  signal?: AbortSignal,
): Promise<AnalyticalEnvelope<Department[]>> {
  return getAnalyticalEnvelope("/api/v1/geography/departments", undefined, signal);
}

export function getMunicipalities(
  departmentCode: string,
  signal?: AbortSignal,
): Promise<AnalyticalEnvelope<Municipality[]>> {
  const params = new URLSearchParams({ department_code: departmentCode });
  return getAnalyticalEnvelope("/api/v1/geography/municipalities", params, signal);
}
