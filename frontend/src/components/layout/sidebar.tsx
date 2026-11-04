"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";
import {
  BarChart3,
  ArrowUpRight,
  Database,
  GitCompareArrows,
  Info,
  LayoutDashboard,
  Sprout,
} from "lucide-react";

const modules = [
  { label: "Resumen General", icon: LayoutDashboard, href: "/", available: true },
  { label: "Consultas avanzadas", icon: BarChart3, href: "/consultas", available: true },
  { label: "Comparador", icon: GitCompareArrows, href: "/comparador", available: true },
  { label: "Repositorio de datos", icon: Database, available: false },
  { label: "Acerca de", icon: Info, available: false },
] as const;

export function Sidebar() {
  const pathname = usePathname();
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
                  <Link
                    aria-label={module.label}
                    className={`sidebar__item ${pathname === module.href ? "sidebar__item--active" : ""}`}
                    aria-current={pathname === module.href ? "page" : undefined}
                    href={module.href}
                  >
                    <Icon size={19} strokeWidth={1.9} aria-hidden="true" />
                    <span>{module.label}</span>
                    <span className="sidebar__active-dot" aria-hidden="true" />
                  </Link>
                ) : (
                  <div className="sidebar__item sidebar__item--disabled" aria-disabled="true">
                    <Icon size={19} strokeWidth={1.9} aria-hidden="true" />
                    <span>{module.label}</span>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      <ThemeToggle />
      <div className="sidebar__footer">
        <span>
          Información oficial del campo colombiano
          <small>
            Datos obtenidos de las Evaluaciones Agropecuarias Municipales (EVA), publicadas
            por la UPRA.
          </small>
          <a href="https://upra.gov.co/es-co/Paginas/eva.aspx" target="_blank" rel="noreferrer">Ver fuente <ArrowUpRight size={13} aria-hidden="true" /></a>
        </span>
      </div>
    </aside>
  );
}
