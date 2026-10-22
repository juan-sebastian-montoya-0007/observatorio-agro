import { ListOrdered } from "lucide-react";
import { useMemo } from "react";

import type { RankingItem } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatIndicator, indicatorLabel, indicatorUnit } from "@/utils/format";

import { EChart } from "../common/echart";

export function CropRanking({
  indicator,
  items,
}: {
  indicator: Indicator;
  items: RankingItem[];
}) {
  const label = indicatorLabel(indicator);
  const unit = indicatorUnit(indicator);
  const option = useMemo(() => {
    const reversed = [...items].reverse();
    return {
      aria: { enabled: true, description: `Ranking de cultivos por ${label}` },
      color: ["#2b8a5e"],
      grid: { left: 92, right: 24, top: 16, bottom: 34 },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: { type: "value", name: unit, splitLine: { lineStyle: { color: "#edf1ef" } } },
      yAxis: {
        type: "category",
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
  }, [items, label, unit]);

  return (
    <article className="panel panel--wide">
      <header className="panel__header">
        <div>
          <span className="panel__eyebrow">Ranking por {label.toLocaleLowerCase("es-CO")}</span>
          <h2>Principales cultivos</h2>
        </div>
        <span className="panel__icon" aria-hidden="true">
          <ListOrdered size={19} />
        </span>
      </header>
      <EChart
        ariaLabel={`Gráfico de principales cultivos por ${label}`}
        items={items.map((item) => ({
          label: item.name,
          value: formatIndicator(item.value, indicator),
        }))}
        option={option}
      />
    </article>
  );
}
