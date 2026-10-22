import { Gauge, ScanLine, Sprout, Wheat } from "lucide-react";

import type { Summary } from "@/types/api";
import { formatArea, formatProduction, formatYield } from "@/utils/format";

export function KpiGrid({ summary }: { summary: Summary }) {
  const items = [
    {
      label: "Área sembrada",
      value: formatArea(summary.planted_area_ha),
      note: "Superficie reportada",
      icon: Sprout,
      tone: "green",
    },
    {
      label: "Área cosechada",
      value: formatArea(summary.harvested_area_ha),
      note: "Superficie productiva",
      icon: ScanLine,
      tone: "teal",
    },
    {
      label: "Producción",
      value: formatProduction(summary.production_t),
      note: "Toneladas obtenidas",
      icon: Wheat,
      tone: "amber",
    },
    {
      label: "Rendimiento",
      value: formatYield(summary.yield_t_ha),
      note: "Razón de sumas",
      icon: Gauge,
      tone: "blue",
    },
  ] as const;

  return (
    <section className="kpi-grid" aria-label="Indicadores principales">
      {items.map(({ icon: Icon, label, note, tone, value }) => (
        <article className="kpi-card" key={label}>
          <span className={`kpi-card__icon kpi-card__icon--${tone}`} aria-hidden="true">
            <Icon size={20} strokeWidth={1.9} />
          </span>
          <div>
            <p>{label}</p>
            <strong>{value}</strong>
            <small>{note}</small>
          </div>
        </article>
      ))}
    </section>
  );
}
