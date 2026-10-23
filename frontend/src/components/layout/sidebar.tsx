import Link from "next/link";
import {
  BarChart3,
  Database,
  GitCompareArrows,
  Info,
  LayoutDashboard,
  Sprout,
} from "lucide-react";

const modules = [
  { label: "Resumen General", icon: LayoutDashboard, href: "/", available: true },
  { label: "Consultas", icon: BarChart3, available: false },
  { label: "Comparador", icon: GitCompareArrows, available: false },
  { label: "Repositorio", icon: Database, available: false },
  { label: "Acerca de", icon: Info, available: false },
] as const;

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand" aria-label="Observatorio Agro">
        <span className="sidebar__brand-mark" aria-hidden="true">
          <Sprout size={23} strokeWidth={2.2} />
        </span>
        <span>
          <strong>Observatorio</strong>
          <strong>Agro</strong>
          <small>Consulta pública</small>
        </span>
      </div>

      <nav className="sidebar__nav" aria-label="Navegación principal">
        <p className="sidebar__eyebrow">Explorar</p>
        <ul>
          {modules.map((module) => {
            const Icon = module.icon;
            return (
              <li key={module.label}>
                {module.available ? (
                  <Link className="sidebar__item sidebar__item--active" href={module.href}>
                    <Icon size={19} strokeWidth={1.9} aria-hidden="true" />
                    <span>{module.label}</span>
                    <span className="sidebar__active-dot" aria-hidden="true" />
                  </Link>
                ) : (
                  <div className="sidebar__item sidebar__item--disabled" aria-disabled="true">
                    <Icon size={19} strokeWidth={1.9} aria-hidden="true" />
                    <span>{module.label}</span>
                    <small>Próximamente</small>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="sidebar__footer">
        <span className="sidebar__status-dot" aria-hidden="true" />
        <span>
          Fuente de datos
          <small>
            Datos obtenidos de las Evaluaciones Agropecuarias Municipales (EVA), publicadas
            por la UPRA.
          </small>
        </span>
      </div>
    </aside>
  );
}
