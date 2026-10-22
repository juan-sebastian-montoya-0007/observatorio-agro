import { AlertCircle, Inbox, RefreshCw } from "lucide-react";

export function DashboardLoading() {
  return (
    <section className="dashboard" role="status" aria-label="Cargando panel agrícola">
      <div className="skeleton skeleton--title" />
      <div className="skeleton skeleton--filters" />
      <div className="kpi-grid">
        {Array.from({ length: 4 }, (_, index) => (
          <div className="skeleton skeleton--kpi" key={index} />
        ))}
      </div>
      <div className="dashboard-grid">
        <div className="skeleton skeleton--chart" />
        <div className="skeleton skeleton--chart" />
      </div>
      <span className="sr-only">Cargando datos agrícolas…</span>
    </section>
  );
}

export function EmptyState({ onReset }: { onReset: () => void }) {
  return (
    <section className="async-state">
      <span className="async-state__icon" aria-hidden="true">
        <Inbox size={25} />
      </span>
      <h2>No hay datos para estos filtros</h2>
      <p>
        La fuente publicada no contiene registros para la combinación territorial,
        temporal y productiva seleccionada.
      </p>
      <button className="button button--primary" type="button" onClick={onReset}>
        Restablecer filtros
      </button>
    </section>
  );
}

export function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <section className="async-state" role="alert">
      <span className="async-state__icon async-state__icon--error" aria-hidden="true">
        <AlertCircle size={25} />
      </span>
      <h2>No pudimos cargar el panel</h2>
      <p>La consulta no se completó. Puedes intentarlo de nuevo sin perder tus filtros.</p>
      <button className="button button--primary" type="button" onClick={onRetry}>
        <RefreshCw size={16} aria-hidden="true" />
        Reintentar
      </button>
    </section>
  );
}
