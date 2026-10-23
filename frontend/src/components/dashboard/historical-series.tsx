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
    grid: { left: 78, right: 24, top: 38, bottom: 58 },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value: number) => `${value} ${config.unit}`,
    },
    xAxis: {
      type: "category",
      name: "Año",
      nameLocation: "middle",
      nameGap: 30,
      boundaryGap: false,
      data: points.map((point) => String(point.year)),
      axisLine: { lineStyle: { color: "#d6dfda" } },
    },
    yAxis: {
      type: "value",
      name: `${config.label} (${config.unit})`,
      nameLocation: "middle",
      nameGap: 58,
      splitLine: { lineStyle: { color: "#edf1ef" } },
    },
    series: [
      {
        data: points.map((point) => Number(point[indicator] ?? 0)),
        type: "line",
        smooth: 0.22,
        symbolSize: 7,
        lineStyle: { width: 3 },
        areaStyle: { color: "rgba(24, 121, 78, 0.08)" },
      },
    ],
  };
}

export function HistoricalSeries({
  indicator,
  points,
}: {
  indicator: Indicator;
  points: SeriesPoint[];
}) {
  const config = indicatorConfig[indicator];
  const option = useMemo(() => buildHistoricalSeriesOption(indicator, points), [indicator, points]);

  return (
    <article className="panel panel--wide">
      <header className="panel__header">
        <div>
          <span className="panel__eyebrow">Evolución 2019–2025</span>
          <h2>Serie histórica</h2>
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
