import { Gauge, ScanLine, Sprout, Wheat } from "lucide-react";

import type { SeriesPoint, Summary } from "@/types/api";
import { formatArea, formatProduction, formatYield } from "@/utils/format";

import { InfoTooltip } from "../common/info-tooltip";

export function KpiGrid({ summary, points = [], year }: { summary: Summary; points?: SeriesPoint[]; year?: number }) {
  const items = [
    {
      label: "Área sembrada",
      key: "planted_area_ha",
      value: formatArea(summary.planted_area_ha),
      note: "Superficie reportada",
      help: "Suma del área reportada como sembrada para los filtros activos. Unidad: hectáreas (ha).",
      icon: Sprout,
      tone: "green",
    },
    {
      label: "Área cosechada",
      key: "harvested_area_ha",
      value: formatArea(summary.harvested_area_ha),
      note: "Superficie productiva",
      help: "Suma del área cosechada reportada para los filtros activos. Unidad: hectáreas (ha).",
      icon: ScanLine,
      tone: "teal",
    },
    {
      label: "Producción",
      key: "production_t",
      value: formatProduction(summary.production_t),
      note: "Toneladas obtenidas",
      help: "Suma de la producción reportada para los filtros activos. Unidad: toneladas (t).",
      icon: Wheat,
      tone: "amber",
    },
    {
      label: "Rendimiento",
      key: "yield_t_ha",
      value: formatYield(summary.yield_t_ha),
      note: "Razón de sumas",
      help: "Producción total dividida por área cosechada total. No es un promedio simple. Unidad: toneladas por hectárea (t/ha).",
      icon: Gauge,
      tone: "blue",
    },
  ] as const;

  return (
    <section className="kpi-grid" aria-label="Indicadores principales">
      {items.map(({ help, icon: Icon, label, note, tone, value, key }) => {
        const history = points.filter((point) => point[key] !== null);
        const numbers = history.map((point) => Number(point[key]));
        const min = Math.min(...numbers);
        const max = Math.max(...numbers);
        const sparkline = numbers.map((number, index) => `${index * 90 / Math.max(1, numbers.length - 1)},${27 - ((number - min) / (max - min || 1)) * 24}`).join(" ");
        const previous = history.find((point) => point.year === (year ?? 0) - 1);
        const previousValue = previous ? Number(previous[key]) : 0;
        const change = previousValue > 0 && summary[key] !== null ? (Number(summary[key]) - previousValue) / previousValue * 100 : null;
        return (
        <article className="kpi-card" key={label}>
          <span className={`kpi-card__icon kpi-card__icon--${tone}`} aria-hidden="true">
            <Icon size={20} strokeWidth={1.9} />
          </span>
          <div className="kpi-card__body">
            <div className="kpi-card__label">
              <p>{label}</p>
              <InfoTooltip
                label={`Información sobre ${label.toLocaleLowerCase("es-CO")}`}
                content={help}
              />
            </div>
            <strong>{value}</strong>
            <div className="kpi-card__bottom">
              <small>{change !== null ? <><span className={`kpi-card__change${change < 0 ? " kpi-card__change--negative" : ""}`}>{change < 0 ? "▼" : "▲"} {Math.abs(change).toLocaleString("es-CO", { maximumFractionDigits: 1 })}%</span> vs {previous!.year}</> : note}</small>
              {numbers.length > 1 && <svg className={`kpi-card__sparkline kpi-card__sparkline--${tone}`} viewBox="0 0 90 30" role="img" aria-label={`Evolución de ${label.toLowerCase()} de ${history[0].year} a ${history[history.length - 1].year}`}><polygon points={`0,30 ${sparkline} 90,30`} fill="currentColor" opacity=".08" /><polyline points={sparkline} fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>}
            </div>
          </div>
        </article>
      ); })}
    </section>
  );
}
