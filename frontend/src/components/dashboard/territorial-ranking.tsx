import { MapPinned } from "lucide-react";

import type { RankingItem } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatIndicator, indicatorLabel, indicatorUnit } from "@/utils/format";

import { InfoTooltip } from "../common/info-tooltip";

export function TerritorialRanking({
  items,
  level,
  indicator,
}: {
  items: RankingItem[];
  level: "department" | "municipality";
  indicator: Indicator;
}) {
  const label = indicatorLabel(indicator);
  const unit = indicatorUnit(indicator);

  return (
    <article className="panel panel--compact">
      <header className="panel__header">
        <div>
          <span className="panel__eyebrow">Lectura territorial</span>
          <h2>{level === "municipality" ? "Municipios líderes" : "Departamentos líderes"}</h2>
        </div>
        <div className="panel__actions">
          <InfoTooltip
            label="Información sobre líderes territoriales"
            content={`Ordena los ${level === "municipality" ? "municipios" : "departamentos"} con mayor ${label.toLocaleLowerCase("es-CO")} para la selección. Unidad: ${unit}.`}
          />
          <span className="panel__icon" aria-hidden="true">
            <MapPinned size={19} />
          </span>
        </div>
      </header>
      <ol className="territory-list">
        {items.map((item) => (
          <li key={item.id}>
            <span className="territory-list__rank">{item.rank}</span>
            <span className="territory-list__name">{item.name}</span>
            <strong>{formatIndicator(item.value, indicator)}</strong>
          </li>
        ))}
      </ol>
    </article>
  );
}
