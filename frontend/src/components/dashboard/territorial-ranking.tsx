import { MapPinned } from "lucide-react";

import type { RankingItem } from "@/types/api";
import type { Indicator } from "@/types/filters";
import { formatIndicator } from "@/utils/format";

export function TerritorialRanking({
  items,
  level,
  indicator,
}: {
  items: RankingItem[];
  level: "department" | "municipality";
  indicator: Indicator;
}) {
  return (
    <article className="panel panel--compact">
      <header className="panel__header">
        <div>
          <span className="panel__eyebrow">Lectura territorial</span>
          <h2>{level === "municipality" ? "Municipios líderes" : "Departamentos líderes"}</h2>
        </div>
        <span className="panel__icon" aria-hidden="true">
          <MapPinned size={19} />
        </span>
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
