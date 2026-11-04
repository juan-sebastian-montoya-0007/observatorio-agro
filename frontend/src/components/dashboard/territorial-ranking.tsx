import type { RankingItem } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatIndicator, indicatorLabel, indicatorUnit } from "@/utils/format";

import { InfoTooltip } from "../common/info-tooltip";

export function TerritorialRanking({
  items,
  level,
  indicator,
  onSelect,
}: {
  items: RankingItem[];
  level: "department" | "municipality";
  indicator: Indicator;
  onSelect?: (code: string) => void;
}) {
  const label = indicatorLabel(indicator);
  const unit = indicatorUnit(indicator);
  const levelLabel = level === "municipality" ? "municipios" : "departamentos";

  return (
    <article className={`panel panel--compact panel--${level === "department" ? "departments" : "municipalities"}`}>
      <header className="panel__header">
        <div>
          <h2>{level === "municipality" ? "Municipios líderes" : "Departamentos líderes"}</h2>
        </div>
        <div className="panel__actions">
          <InfoTooltip
            label="Información sobre líderes territoriales"
            content={`Ordena los ${levelLabel} con mayor ${label.toLocaleLowerCase("es-CO")} para la selección. Unidad: ${unit}.`}
          />
        </div>
      </header>
      <p className="panel__caption">Por {label.toLocaleLowerCase("es-CO")} · {unit}</p>
      <div className="territory-list__head"><span>#</span><span>{level === "department" ? "Departamento" : "Municipio"}</span><span>{label} ({unit})</span></div>
      <ol className="territory-list" aria-label={`Ranking de ${levelLabel} por ${label} (${unit})`}>
        {items.map((item) => (
          <li key={item.id}>
            <span className="territory-list__rank">{item.rank}</span>
            {onSelect ? <button className="territory-list__name" onClick={() => onSelect(String(item.id))} type="button" title={item.name}>{item.name}</button> : <span className="territory-list__name" title={item.name}>{item.name}</span>}
            <strong>{formatIndicator(item.value, indicator)}</strong>
          </li>
        ))}
      </ol>
    </article>
  );
}
