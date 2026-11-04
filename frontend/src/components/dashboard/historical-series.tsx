import { TrendingUp } from "lucide-react";
import { useMemo } from "react";

import type { SeriesPoint } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatArea, formatProduction, formatYield } from "@/utils/format";

import { EChart } from "../common/echart";
import { InfoTooltip } from "../common/info-tooltip";

const indicatorConfig = {
  planted_area_ha: { label: "Área sembrada", unit: "ha", format: formatArea },
  harvested_area_ha: { label: "Área cosechada", unit: "ha", format: formatArea },
  production_t: { label: "Producción", unit: "t", format: formatProduction },
  yield_t_ha: { label: "Rendimiento", unit: "t/ha", format: formatYield },
} as const;

export function buildHistoricalSeriesOption(indicator: Indicator, points: SeriesPoint[]) {
  const config = indicatorConfig[indicator];
  return {
    animationDuration: 450,
    aria: {
      enabled: true,
      description: `Serie histórica de ${config.label}; eje horizontal: Año; eje vertical: ${config.label} (${config.unit})`,
    },
    color: ["#18794e"],
    grid: { left: 62, right: 13, top: 16, bottom: 43 },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value: number) => `${value} ${config.unit}`,
    },
    xAxis: {
      type: "category",
      name: "Año",
      nameLocation: "middle",
      nameGap: 25,
      nameTextStyle: { fontSize: 9 },
      axisLabel: { fontSize: 9 },
      boundaryGap: false,
      data: points.map((point) => String(point.year)),
      axisLine: { lineStyle: { color: "#d6dfda" } },
    },
    yAxis: {
      type: "value",
      name: `${config.label} (${config.unit})`,
      nameLocation: "middle",
      nameGap: 49,
      nameTextStyle: { fontSize: 9 },
      axisLabel: { fontSize: 8, formatter: (value: number) => new Intl.NumberFormat("es-CO", { notation: "compact", maximumFractionDigits: 1 }).format(value) },
      splitLine: { lineStyle: { color: "#edf1ef" } },
    },
    series: [
      {
        data: points.map((point) => Number(point[indicator] ?? 0)),
        type: "line",
        smooth: 0.22,
        symbolSize: 6,
        lineStyle: { width: 2 },
        areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(55, 151, 75, .43)" }, { offset: 1, color: "rgba(55, 151, 75, .03)" }] } },
      },
    ],
  };
}

export function HistoricalSeries({
  indicator,
  points,
  onIndicatorChange,
}: {
  indicator: Indicator;
  points: SeriesPoint[];
  onIndicatorChange?: (indicator: Indicator) => void;
}) {
  const config = indicatorConfig[indicator];
  const option = useMemo(() => buildHistoricalSeriesOption(indicator, points), [indicator, points]);

  return (
    <article className="panel panel--history">
      <header className="panel__header">
        <div>
          <h2>Evolución histórica <span className="panel__muted">{points[0]?.year ?? 2019} – {points[points.length - 1]?.year ?? 2025}</span></h2>
        </div>
        <div className="panel__actions">
          <InfoTooltip
            label="Información sobre la serie histórica"
            content={`Muestra la evolución anual de ${config.label.toLocaleLowerCase("es-CO")} en ${config.unit} para los filtros activos.`}
          />
          <span className="panel__icon" aria-hidden="true">
            <TrendingUp size={19} />
          </span>
        </div>
      </header>
      <div className="metric-tabs" aria-label="Indicador de la serie histórica">
        {(Object.keys(indicatorConfig) as Indicator[]).map((key) => <button type="button" key={key} className={indicator === key ? "is-active" : ""} aria-pressed={indicator === key} onClick={() => onIndicatorChange?.(key)}>{indicatorConfig[key].label}</button>)}
      </div>
      <EChart
        ariaLabel={`Gráfico de ${config.label}; eje horizontal: Año; eje vertical: ${config.label} (${config.unit})`}
        items={points.map((point) => ({
          label: `${point.year} · ${point.period_type}`,
          value: config.format(point[indicator]),
        }))}
        option={option}
      />
    </article>
  );
}
