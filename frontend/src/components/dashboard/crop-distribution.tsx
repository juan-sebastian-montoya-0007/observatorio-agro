import { ChartPie } from "lucide-react";
import { useMemo } from "react";

import type { RankingItem } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatIndicator, indicatorLabel, indicatorUnit } from "@/utils/format";

import { EChart } from "../common/echart";

export function CropDistribution({
  indicator,
  items,
}: {
  indicator: Indicator;
  items: RankingItem[];
}) {
  const label = indicatorLabel(indicator);
  const unit = indicatorUnit(indicator);
  const option = useMemo(
    () => ({
      aria: { enabled: true, description: `Distribución de ${label} por cultivo` },
      color: ["#176b45", "#42a579", "#85c7a7", "#d5a537", "#6c8796"],
      tooltip: { trigger: "item", formatter: `{b}: {c} ${unit} ({d}%)` },
      legend: { bottom: 0, type: "scroll", itemWidth: 9, itemHeight: 9 },
      series: [
        {
          type: "pie",
          radius: ["48%", "70%"],
          center: ["50%", "43%"],
          avoidLabelOverlap: true,
          label: { show: false },
          itemStyle: { borderColor: "#fff", borderWidth: 3 },
          data: items.map((item) => ({ name: item.name, value: Number(item.value) })),
        },
      ],
    }),
    [items, label, unit],
  );

  return (
    <article className="panel panel--compact">
      <header className="panel__header">
        <div>
          <span className="panel__eyebrow">Composición</span>
          <h2>Distribución por cultivo</h2>
        </div>
        <span className="panel__icon" aria-hidden="true">
          <ChartPie size={19} />
        </span>
      </header>
      <EChart
        ariaLabel={`Gráfico de distribución de ${label} por cultivo`}
        items={items.map((item) => ({
          label: item.name,
          value: formatIndicator(item.value, indicator),
        }))}
        option={option}
      />
    </article>
  );
}
