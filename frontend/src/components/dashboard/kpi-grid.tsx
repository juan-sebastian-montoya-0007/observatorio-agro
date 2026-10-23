import { Gauge, ScanLine, Sprout, Wheat } from "lucide-react";

import type { Summary } from "@/types/api";
import { formatArea, formatProduction, formatYield } from "@/utils/format";

import { InfoTooltip } from "../common/info-tooltip";

export function KpiGrid({ summary }: { summary: Summary }) {
  const items = [
    {
      label: "Área sembrada",
      value: formatArea(summary.planted_area_ha),
      note: "Superficie reportada",
      help: "Suma del área reportada como sembrada para los filtros activos. Unidad: hectáreas (ha).",
      icon: Sprout,
      tone: "green",
    },
    {
      label: "Área cosechada",
      value: formatArea(summary.harvested_area_ha),
      note: "Superficie productiva",
      help: "Suma del área cosechada reportada para los filtros activos. Unidad: hectáreas (ha).",
      icon: ScanLine,
      tone: "teal",
    },
    {
      label: "Producción",
      value: formatProduction(summary.production_t),
      note: "Toneladas obtenidas",
      help: "Suma de la producción reportada para los filtros activos. Unidad: toneladas (t).",
      icon: Wheat,
      tone: "amber",
    },
    {
      label: "Rendimiento",
      value: formatYield(summary.yield_t_ha),
      note: "Razón de sumas",
      help: "Producción total dividida por área cosechada total. No es un promedio simple. Unidad: toneladas por hectárea (t/ha).",
      icon: Gauge,
      tone: "blue",
    },
  ] as const;

  return (
    <section className="kpi-grid" aria-label="Indicadores principales">
      {items.map(({ help, icon: Icon, label, note, tone, value }) => (
        <article className="kpi-card" key={label}>
          <span className={`kpi-card__icon kpi-card__icon--${tone}`} aria-hidden="true">
            <Icon size={20} strokeWidth={1.9} />
          </span>
          <div>
            <div className="kpi-card__label">
              <p>{label}</p>
              <InfoTooltip
                label={`Información sobre ${label.toLocaleLowerCase("es-CO")}`}
                content={help}
              />
            </div>
            <strong>{value}</strong>
            <small>{note}</small>
          </div>
        </article>
      ))}
    </section>
  );
}
