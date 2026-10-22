"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import type {
  DashboardFilters,
  Indicator,
  PeriodMode,
} from "@/types/filters";

export const DEFAULT_DASHBOARD_FILTERS: DashboardFilters = {
  year: 2025,
  periodMode: "AGRICULTURAL_YEAR",
  indicator: "production_t",
};

const PERIOD_MODES = new Set<PeriodMode>(["SOURCE", "AGRICULTURAL_YEAR"]);
const INDICATORS = new Set<Indicator>([
  "planted_area_ha",
  "harvested_area_ha",
  "production_t",
  "yield_t_ha",
]);

function optionalCode(value: string | null, digits: number): string | undefined {
  return value !== null && new RegExp(`^\\d{${digits}}$`).test(value)
    ? value
    : undefined;
}

function optionalPositiveInteger(value: string | null): number | undefined {
  if (value === null || !/^\d+$/.test(value)) return undefined;
  const parsed = Number(value);
  return parsed > 0 ? parsed : undefined;
}

function optionalText(value: string | null): string | undefined {
  const normalized = value?.trim();
  return normalized ? normalized : undefined;
}

export function readFilters(
  search: string | URLSearchParams | { toString(): string },
): DashboardFilters {
  const params =
    typeof search === "string"
      ? new URLSearchParams(search.startsWith("?") ? search.slice(1) : search)
      : new URLSearchParams(search.toString());
  const department = optionalCode(params.get("department"), 2);
  const municipalityCandidate = optionalCode(params.get("municipality"), 5);
  const municipality =
    department && municipalityCandidate?.startsWith(department)
      ? municipalityCandidate
      : undefined;
  const rawYear = params.get("year");
  const parsedYear = rawYear !== null && /^\d{4}$/.test(rawYear) ? Number(rawYear) : 0;
  const year = parsedYear >= 2019 && parsedYear <= 2025 ? parsedYear : 2025;
  const rawMode = params.get("period_mode") as PeriodMode | null;
  const periodMode = rawMode && PERIOD_MODES.has(rawMode) ? rawMode : "AGRICULTURAL_YEAR";
  const rawIndicator = params.get("indicator") as Indicator | null;
  const indicator =
    rawIndicator && INDICATORS.has(rawIndicator) ? rawIndicator : "production_t";

  return {
    ...(department ? { department } : {}),
    ...(municipality ? { municipality } : {}),
    ...(optionalPositiveInteger(params.get("crop")) !== undefined
      ? { crop: optionalPositiveInteger(params.get("crop")) }
      : {}),
    ...(optionalPositiveInteger(params.get("crop_variant")) !== undefined
      ? { cropVariant: optionalPositiveInteger(params.get("crop_variant")) }
      : {}),
    ...(optionalText(params.get("group")) ? { group: optionalText(params.get("group")) } : {}),
    ...(optionalText(params.get("subgroup"))
      ? { subgroup: optionalText(params.get("subgroup")) }
      : {}),
    ...(optionalText(params.get("cycle")) ? { cycle: optionalText(params.get("cycle")) } : {}),
    ...(optionalText(params.get("physical_state"))
      ? { physicalState: optionalText(params.get("physical_state")) }
      : {}),
    year,
    periodMode,
    indicator,
  };
}

export function writeFilters(filters: DashboardFilters): URLSearchParams {
  const params = new URLSearchParams({
    year: String(filters.year),
    period_mode: filters.periodMode,
    indicator: filters.indicator,
  });
  const values: Array<[string, string | number | undefined]> = [
    ["department", filters.department],
    ["municipality", filters.municipality],
    ["crop", filters.crop],
    ["crop_variant", filters.cropVariant],
    ["group", filters.group],
    ["subgroup", filters.subgroup],
    ["cycle", filters.cycle],
    ["physical_state", filters.physicalState],
  ];
  for (const [key, value] of values) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  return params;
}

export function clearDepartment(filters: DashboardFilters): DashboardFilters {
  const remaining = { ...filters };
  delete remaining.department;
  delete remaining.municipality;
  return remaining;
}

export function updateFilter<K extends keyof DashboardFilters>(
  filters: DashboardFilters,
  key: K,
  value: DashboardFilters[K] | undefined,
): DashboardFilters {
  const next = { ...filters, [key]: value } as DashboardFilters;
  if (value === undefined) delete next[key];
  if (key === "department" && value !== filters.department) {
    delete next.municipality;
  }
  if (key === "municipality" && !next.department) {
    delete next.municipality;
  }
  return next;
}

export function useDashboardFilters() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);

  const setFilter = useCallback(
    <K extends keyof DashboardFilters>(
      key: K,
      value: DashboardFilters[K] | undefined,
    ) => {
      const query = writeFilters(updateFilter(filters, key, value)).toString();
      router.replace(`${pathname}?${query}`, { scroll: false });
    },
    [filters, pathname, router],
  );

  const resetFilters = useCallback(() => {
    router.replace(pathname, { scroll: false });
  }, [pathname, router]);

  return { filters, setFilter, resetFilters };
}
