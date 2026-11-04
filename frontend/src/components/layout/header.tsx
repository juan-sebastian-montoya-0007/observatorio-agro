"use client";

import { Download, Info, Search, Share2 } from "lucide-react";
import { useEffect, useState } from "react";

export function Header() {
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const showResult = (event: Event) => setNotice((event as CustomEvent<string>).detail);
    window.addEventListener("agro:search-result", showResult);
    return () => window.removeEventListener("agro:search-result", showResult);
  }, []);
  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setNotice("Enlace de esta consulta copiado");
    } catch {
      setNotice("Copia la dirección del navegador para compartir esta consulta.");
    }
  };
  return (
    <header className="app-header">
      <h1 className="sr-only">Observatorio Agro</h1>
      <form className="app-header__search" role="search" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); window.dispatchEvent(new CustomEvent("agro:search", { detail: String(data.get("query") ?? "") })); }}>
        <Search size={15} aria-hidden="true" />
        <input type="search" name="query" aria-label="Buscar cultivos o departamentos" placeholder="Buscar cultivos o departamentos…" />
      </form>
      <span className="app-header__notice" role="status">{notice}</span>
      <div className="app-header__actions">
        <button type="button" className="button button--outline" onClick={() => window.dispatchEvent(new Event("agro:export"))} title="Descargar los indicadores de la consulta en CSV"><Download size={14} aria-hidden="true" /><span>Exportar</span></button>
        <button type="button" className="button button--outline" onClick={share}><Share2 size={14} aria-hidden="true" /><span>Compartir</span></button>
        <a href="#fuente-datos" className="app-header__help" aria-label="Fuente de los datos"><Info size={16} /></a>
      </div>
    </header>
  );
}
