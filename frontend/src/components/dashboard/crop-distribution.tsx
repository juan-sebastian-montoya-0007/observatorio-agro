import { useMemo } from "react";

import type { RankingItem } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatIndicator, indicatorLabel, indicatorUnit } from "@/utils/format";

import { EChart } from "../common/echart";
import { InfoTooltip } from "../common/info-tooltip";

export function CropDistribution({
  indicator,
  items,
}: {
  indicator: Indicator;
  items: RankingItem[];
}) {
  const label = indicatorLabel(indicator);
  const unit = indicatorUnit(indicator);
  const labelWithUnit = `${label} (${unit})`;
  const option = useMemo(
    () => ({
      aria: { enabled: true, description: `Distribución de ${labelWithUnit} por cultivo` },
      color: ["#176b45", "#42a579", "#85c7a7", "#d5a537", "#6c8796"],
      tooltip: { trigger: "item", formatter: `{b}: {c} ${unit} ({d}%)` },
      legend: { right: 0, top: "middle", orient: "vertical", type: "scroll", itemWidth: 6, itemHeight: 6, textStyle: { fontSize: 8, width: 75, overflow: "truncate" } },
      series: [
        {
          type: "pie",
          radius: ["40%", "63%"],
          center: ["33%", "50%"],
          avoidLabelOverlap: true,
          label: { show: false },
          itemStyle: { borderColor: "#fff", borderWidth: 3 },
          data: items.map((item) => ({ name: item.name, value: Number(item.value) })),
        },
      ],
    }),
    [items, labelWithUnit, unit],
  );

  return (
    <article className="panel panel--compact panel--distribution">
      <header className="panel__header">
        <div>
          <h2>Composición por cultivo</h2>
        </div>
        <div className="panel__actions">
          <InfoTooltip
            label="Información sobre distribución por cultivo"
            content={`Compara la participación de los cinco cultivos principales en ${label.toLocaleLowerCase("es-CO")}. El tooltip muestra valor, ${unit} y porcentaje.`}
          />
        </div>
      </header>
      <p className="panel__caption">Cinco principales · {label.toLocaleLowerCase("es-CO")} ({unit})</p>
      <EChart
        ariaLabel={`Distribución de ${labelWithUnit} por cultivo`}
        items={items.map((item) => ({
          label: item.name,
          value: formatIndicator(item.value, indicator),
        }))}
        option={option}
      />
      <p className="panel__footnote">Participación entre los cinco cultivos mostrados.</p>
    </article>
  );
}
