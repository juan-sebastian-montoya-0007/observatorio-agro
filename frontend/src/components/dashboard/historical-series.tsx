import { TrendingUp } from "lucide-react";
import { useMemo } from "react";

import type { SeriesPoint } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatArea, formatProduction, formatYield } from "@/utils/format";

import { EChart } from "../common/echart";

const indicatorConfig = {
  planted_area_ha: { label: "Área sembrada", unit: "ha", format: formatArea },
  harvested_area_ha: { label: "Área cosechada", unit: "ha", format: formatArea },
  production_t: { label: "Producción", unit: "t", format: formatProduction },
  yield_t_ha: { label: "Rendimiento", unit: "t/ha", format: formatYield },
} as const;

export function HistoricalSeries({
  indicator,
  points,
}: {
  indicator: Indicator;
  points: SeriesPoint[];
}) {
  const config = indicatorConfig[indicator];
  const option = useMemo(
    () => ({
      animationDuration: 450,
      aria: { enabled: true, description: `Serie histórica de ${config.label}` },
      color: ["#18794e"],
      grid: { left: 52, right: 18, top: 28, bottom: 38 },
      tooltip: { trigger: "axis", valueFormatter: (value: number) => `${value} ${config.unit}` },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: points.map((point) => String(point.year)),
        axisLine: { lineStyle: { color: "#d6dfda" } },
      },
      yAxis: {
        type: "value",
        name: config.unit,
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
    }),
    [config, indicator, points],
  );

  return (
    <article className="panel panel--wide">
      <header className="panel__header">
        <div>
          <span className="panel__eyebrow">Evolución 2019–2025</span>
          <h2>Serie histórica</h2>
        </div>
        <span className="panel__icon" aria-hidden="true">
          <TrendingUp size={19} />
        </span>
      </header>
      <EChart
        ariaLabel={`Gráfico de ${config.label} por año`}
        items={points.map((point) => ({
          label: `${point.year} · ${point.period_type}`,
          value: config.format(point[indicator]),
        }))}
        option={option}
      />
    </article>
  );
}
