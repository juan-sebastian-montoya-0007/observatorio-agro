import { ListOrdered } from "lucide-react";

import type { RankingItem } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatIndicator, indicatorLabel, indicatorUnit } from "@/utils/format";

import { EChart } from "../common/echart";
import { InfoTooltip } from "../common/info-tooltip";

const compactAxisFormatter = new Intl.NumberFormat("es-CO", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function buildCropRankingOption(indicator: Indicator, items: RankingItem[]) {
  const label = indicatorLabel(indicator);
  const unit = indicatorUnit(indicator);
  const reversed = [...items].reverse();
  return {
    aria: {
      enabled: true,
      description: `Ranking de cultivos; eje horizontal: ${label} (${unit}); eje vertical: Cultivo`,
    },
    color: ["#2b8a5e"],
    grid: { left: 108, right: 28, top: 36, bottom: 58 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: (value: number) => formatIndicator(value, indicator),
    },
    xAxis: {
      type: "value",
      name: `${label} (${unit})`,
      nameLocation: "middle",
      nameGap: 32,
      axisLabel: {
        formatter: (value: number) => compactAxisFormatter.format(value),
      },
      splitLine: { lineStyle: { color: "#edf1ef" } },
    },
    yAxis: {
      type: "category",
      name: "Cultivo",
      data: reversed.map((item) => item.name),
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: reversed.map((item) => Number(item.value)),
        barMaxWidth: 18,
        itemStyle: { borderRadius: [0, 5, 5, 0] },
      },
    ],
  };
}

export function CropRanking({
  indicator,
  items,
}: {
  indicator: Indicator;
  items: RankingItem[];
}) {
  const label = indicatorLabel(indicator);
  const unit = indicatorUnit(indicator);
  const option = buildCropRankingOption(indicator, items);

  return (
    <article className="panel panel--wide">
      <header className="panel__header">
        <div>
          <span className="panel__eyebrow">Ranking por {label.toLocaleLowerCase("es-CO")}</span>
          <h2>Principales cultivos</h2>
        </div>
        <div className="panel__actions">
          <InfoTooltip
            label="Información sobre principales cultivos"
            content={`Ordena los cultivos con mayor ${label.toLocaleLowerCase("es-CO")} para la selección. Los valores se expresan en ${unit}.`}
          />
          <span className="panel__icon" aria-hidden="true">
            <ListOrdered size={19} />
          </span>
        </div>
      </header>
      <EChart
        ariaLabel={`Gráfico de principales cultivos; eje horizontal: ${label} (${unit}); eje vertical: Cultivo`}
        items={items.map((item) => ({
          label: item.name,
          value: formatIndicator(item.value, indicator),
        }))}
        option={option}
      />
    </article>
  );
}
