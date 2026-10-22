import type { DecimalValue } from "@/types/api";

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
