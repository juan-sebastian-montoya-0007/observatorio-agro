import type { DecimalValue } from "@/types/api";
import type { Indicator } from "@/types/filters";

export type MetricValue = DecimalValue | number | null | undefined;

const decimalFormatter = new Intl.NumberFormat("es-CO", {
  maximumFractionDigits: 2,
});

export function formatMetric(value: MetricValue): string {
  if (value === null || value === undefined || value === "") return "No disponible";
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? decimalFormatter.format(parsed) : "No disponible";
}

function formatWithUnit(value: MetricValue, unit: string): string {
  const formatted = formatMetric(value);
  return formatted === "No disponible" ? formatted : `${formatted} ${unit}`;
}

export function formatArea(value: MetricValue): string {
  return formatWithUnit(value, "ha");
}

export function formatProduction(value: MetricValue): string {
  return formatWithUnit(value, "t");
}

export function formatYield(value: MetricValue): string {
  return formatWithUnit(value, "t/ha");
}

export function indicatorLabel(indicator: Indicator): string {
  return {
    planted_area_ha: "Área sembrada",
    harvested_area_ha: "Área cosechada",
    production_t: "Producción",
    yield_t_ha: "Rendimiento",
  }[indicator];
}

export function indicatorUnit(indicator: Indicator): string {
  return {
    planted_area_ha: "ha",
    harvested_area_ha: "ha",
    production_t: "t",
    yield_t_ha: "t/ha",
  }[indicator];
}

export function formatIndicator(value: MetricValue, indicator: Indicator): string {
  return formatWithUnit(value, indicatorUnit(indicator));
}
