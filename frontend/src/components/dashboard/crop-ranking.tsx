import { ListOrdered } from "lucide-react";

import type { RankingItem } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatIndicator, indicatorLabel, indicatorUnit } from "@/utils/format";

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
  onSelect,
}: {
  indicator: Indicator;
  items: RankingItem[];
  onSelect?: (id: string | number) => void;
}) {
  const label = indicatorLabel(indicator);
  const unit = indicatorUnit(indicator);
  const maximum = Math.max(...items.map((item) => Number(item.value)), 1);

  return (
    <article className="panel panel--crops">
      <header className="panel__header">
        <div>
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
      <p className="panel__caption">Por {label.toLocaleLowerCase("es-CO")} · {unit}</p>
      <div className="crop-bars" role="table" aria-label={`Principales cultivos: ${label} (${unit})`}>
        <div className="sr-only" role="row"><span role="columnheader">Cultivo</span><span role="columnheader">{label} ({unit})</span></div>
        {items.map((item) => <div className="crop-bars__row" role="row" key={item.id}><span className="crop-bars__rank" aria-hidden="true">{item.rank}</span><button type="button" role="cell" onClick={() => onSelect?.(item.id)} title={`Filtrar por ${item.name}`}>{item.name}</button><span className="crop-bars__track" aria-hidden="true"><span style={{ width: `${Number(item.value) / maximum * 100}%` }} /></span><strong role="cell">{formatIndicator(item.value, indicator)}</strong></div>)}
      </div>
      <p className="panel__footnote">Selecciona un cultivo para explorar sus datos.</p>
    </article>
  );
}
