import { BookOpen, ChevronRight } from "lucide-react";

export function Header() {
  return (
    <header className="app-header">
      <div>
        <div className="app-header__breadcrumb" aria-label="Ruta actual">
          <span>Analítica agrícola</span>
          <ChevronRight size={14} aria-hidden="true" />
          <strong>Resumen General</strong>
        </div>
        <h1>EVA Explorer</h1>
      </div>
      <a className="source-link" href="#fuente-datos">
        <BookOpen size={17} aria-hidden="true" />
        Fuentes y metodología
      </a>
    </header>
  );
}
