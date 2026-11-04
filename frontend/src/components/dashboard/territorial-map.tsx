"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MapPinned, Minus, Plus, RotateCcw } from "lucide-react";

import { getTerritorialMap, type MapFeature, type TerritorialMapData } from "@/services/map";
import type { AnalyticalEnvelope } from "@/types/api";
import type { DashboardFilters } from "@/types/filters";

type Props = {
  filters: DashboardFilters;
  tone?: 'green' | 'blue';
  scaleMax?: number;
  onSelect?: (level: "department" | "municipality", code: string) => void;
};

const COLORS = ["#dceee2", "#a9d5b6", "#6fb28c", "#35865b", "#125139"];
const NO_DATA = "#e6eae7";
const LABELS = {
  production_t: "Producción",
  planted_area_ha: "Área sembrada",
  harvested_area_ha: "Área cosechada",
  yield_t_ha: "Rendimiento",
};
const number = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });
const compact = new Intl.NumberFormat("es-CO", { notation: "compact", maximumFractionDigits: 1 });

function rings(feature: MapFeature) {
  return feature.geometry.type === "Polygon"
    ? feature.geometry.coordinates
    : feature.geometry.coordinates.flat();
}

function MapCanvas({ data, unit, onSelect, selected, tone, scaleMax }: {
  data: TerritorialMapData;
  unit: string;
  onSelect: Props["onSelect"];
  selected?: string;
  tone?: 'green' | 'blue';
  scaleMax?: number;
}) {
  const COLORS = tone === 'blue' ? ['#e2edff', '#b7d3ff', '#79acff', '#4385ee', '#2458c8'] : ['#dceee2', '#a9d5b6', '#6fb28c', '#35865b', '#125139'];
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<{ x: number; y: number; offsetX: number; offsetY: number; moved: boolean } | null>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [hovered, setHovered] = useState<MapFeature | null>(null);
  const shape = useMemo(() => {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    const paths = data.geojson.features.map((feature) => {
      const path = rings(feature).map((ring) => ring.map(([lon, lat], index) => {
        // Equirectangular projection, preserving the official polygon coordinates.
        const x = lon, y = -lat;
        minX = Math.min(minX, x); maxX = Math.max(maxX, x);
        minY = Math.min(minY, y); maxY = Math.max(maxY, y);
        return `${index ? "L" : "M"}${x},${y}`;
      }).join(" ") + "Z").join(" ");
      return { feature, path };
    });
    const width = maxX - minX || 1, height = maxY - minY || 1;
    const pad = Math.max(width, height) * 0.035;
    return { paths, x: minX - pad, y: minY - pad, width: width + pad * 2, height: height + pad * 2 };
  }, [data.geojson]);
  const values = data.geojson.features.flatMap(({ properties }) => properties.value === null ? [] : [properties.value]);
  const max = Math.max(0, scaleMax ?? 0, ...values);
  const viewWidth = shape.width / zoom, viewHeight = shape.height / zoom;
  const viewBox = `${shape.x + (shape.width - viewWidth) / 2 + offset.x} ${shape.y + (shape.height - viewHeight) / 2 + offset.y} ${viewWidth} ${viewHeight}`;

  if (!shape.paths.length) return <p role="status">No hay geometría disponible para este territorio.</p>;

  return (
    <>
      <div className="territorial-map__toolbar" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginTop: 14 }}>
        <span style={{ color: "var(--ink-500)", fontSize: 11 }}>
          {data.level === "department" ? "Selecciona un departamento" : "Selecciona un municipio"}
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          <button type="button" className="button button--quiet" aria-label="Acercar mapa" onClick={() => setZoom((value) => Math.min(8, value * 1.5))} disabled={zoom >= 8}><Plus size={14} /></button>
          <button type="button" className="button button--quiet" aria-label="Alejar mapa" onClick={() => setZoom((value) => Math.max(1, value / 1.5))} disabled={zoom <= 1}><Minus size={14} /></button>
          <button type="button" className="button button--quiet" aria-label="Restablecer mapa" onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }); }}><RotateCcw size={13} /></button>
        </div>
      </div>
      <div className="territorial-map__canvas" style={{ position: "relative", height: 430, marginTop: 8, overflow: "hidden", borderRadius: 8, background: "#f7faf8" }}>
        <svg
          ref={svgRef}
          viewBox={viewBox}
          aria-label={`Mapa de ${data.level === "department" ? "departamentos de Colombia" : "municipios del departamento"}`}
          style={{ width: "100%", height: "100%", touchAction: zoom > 1 ? "none" : "pan-y", cursor: zoom > 1 ? "grab" : "default" }}
          onPointerDown={(event) => {
            if (zoom <= 1) return;
            drag.current = { x: event.clientX, y: event.clientY, offsetX: offset.x, offsetY: offset.y, moved: false };
          }}
          onPointerMove={(event) => {
            if (!drag.current || !svgRef.current) return;
            const rect = svgRef.current.getBoundingClientRect();
            const scale = Math.max(viewWidth / rect.width, viewHeight / rect.height);
            const dx = event.clientX - drag.current.x, dy = event.clientY - drag.current.y;
            if (Math.abs(dx) + Math.abs(dy) > 5) {
              drag.current.moved = true;
              svgRef.current.setPointerCapture(event.pointerId);
              setOffset({ x: drag.current.offsetX - dx * scale, y: drag.current.offsetY - dy * scale });
            }
          }}
          onPointerUp={() => { if (drag.current && !drag.current.moved) drag.current = null; }}
          onPointerCancel={() => { drag.current = null; }}
          onPointerLeave={() => { setHovered(null); }}
        >
          <title>Cartografía oficial DANE · Marco Geoestadístico Nacional 2025</title>
          {shape.paths.map(({ feature, path }) => {
            const { code, name, value } = feature.properties;
            const color = value === null ? NO_DATA : COLORS[max ? Math.min(4, Math.floor(value / max * 5)) : 0];
            const label = `${name}: ${value === null ? "Sin datos" : `${number.format(value)} ${unit}`}`;
            return (
              <path
                key={code}
                d={path}
                fill={color}
                fillRule="evenodd"
                stroke={selected === code || hovered?.properties.code === code ? "#d49932" : "#ffffff"}
                strokeWidth={selected === code || hovered?.properties.code === code ? 2 : 0.7}
                vectorEffect="non-scaling-stroke"
                tabIndex={0}
                role="button"
                aria-label={label}
                aria-pressed={selected === code}
                style={{ cursor: "pointer", outlineOffset: 2 }}
                onMouseEnter={() => setHovered(feature)}
                onFocus={() => setHovered(feature)}
                onBlur={() => setHovered(null)}
                onClick={() => {
                  if (drag.current?.moved) { drag.current = null; return; }
                  onSelect?.(data.level, code);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect?.(data.level, code);
                  }
                }}
              ><title>{label}</title></path>
            );
          })}
        </svg>
        {hovered && <div role="status" style={{ position: "absolute", left: 12, bottom: 12, maxWidth: "calc(100% - 24px)", pointerEvents: "none", border: "1px solid var(--line)", background: "white", boxShadow: "0 3px 16px #123d2d15", padding: "10px 13px", borderRadius: 7, fontSize: 12 }}>
          <strong style={{ display: "block", marginBottom: 3 }}>{hovered.properties.name}</strong>
          {hovered.properties.value === null ? "Sin datos para estos filtros" : `${number.format(hovered.properties.value)} ${unit}`}
          <small style={{ display: "block", color: "var(--ink-500)", marginTop: 3 }}>DIVIPOLA {hovered.properties.code}</small>
        </div>}
      </div>
      <div className="territorial-map__legend" aria-label={`Escala del indicador en ${unit}`} style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 12, padding: "14px 0 8px", color: "var(--ink-700)", fontSize: 11 }}>
        {values.length > 0 && <>
          <span>0 {unit}</span>
          <span style={{ display: "flex", width: 150, height: 9, borderRadius: 3, overflow: "hidden" }} aria-hidden="true">{COLORS.map((color) => <span key={color} style={{ background: color, flex: 1 }} />)}</span>
          <span>{compact.format(max)} {unit}</span>
        </>}
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><i style={{ display: "inline-block", width: 12, height: 9, background: NO_DATA, border: "1px solid #ccd5ce", borderRadius: 2 }} />Sin datos</span>
        <span style={{ marginLeft: "auto", color: "var(--ink-500)" }}>{values.length} de {shape.paths.length} territorios con dato</span>
      </div>
      {values.length === 0 && <p role="status" style={{ color: "var(--ink-500)", fontSize: 12 }}>No hay datos para los filtros seleccionados.</p>}
      {data.unmatched_codes.length > 0 && <p role="status" style={{ color: "#80651e", fontSize: 11 }}>{data.unmatched_codes.length} territorios con datos no tienen geometría disponible.</p>}
    </>
  );
}

export function TerritorialMap({ filters, onSelect, tone, scaleMax }: Props) {
  const filterKey = JSON.stringify(filters);
  const [result, setResult] = useState<{ key: string; envelope?: AnalyticalEnvelope<TerritorialMapData>; error?: string } | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getTerritorialMap(JSON.parse(filterKey) as DashboardFilters, controller.signal)
      .then((envelope) => { if (!controller.signal.aborted) setResult({ key: filterKey, envelope }); })
      .catch(() => { if (!controller.signal.aborted) setResult({ key: filterKey, error: "No se pudo cargar el mapa territorial." }); });
    return () => controller.abort();
  }, [filterKey, attempt]);

  const current = result?.key === filterKey ? result : null;
  const data = current?.envelope?.data;
  const unit = current?.envelope?.meta.unit ?? (filters.indicator === "yield_t_ha" ? "t/ha" : filters.indicator === "production_t" ? "t" : "ha");
  return (
    <article className="panel panel--map" aria-busy={!current}>
      <header className="panel__header">
        <div><span className="panel__eyebrow">Distribución territorial</span><h2>{LABELS[filters.indicator]} por {filters.department ? "municipio" : "departamento"}</h2></div>
        <span className="panel__icon" aria-hidden="true"><MapPinned size={19} /></span>
      </header>
      {!current && <div role="status" style={{ minHeight: 480, display: "grid", placeItems: "center", color: "var(--ink-500)", fontSize: 13 }}>Cargando cartografía oficial…</div>}
      {current?.error && <div role="status" style={{ minHeight: 480, display: "grid", alignContent: "center", justifyItems: "center", gap: 12 }}><p>{current.error}</p><button className="button button--quiet" onClick={() => { setResult(null); setAttempt((value) => value + 1); }}>Reintentar mapa</button></div>}
      {data && <>
        <MapCanvas key={`${data.level}-${filters.department ?? "CO"}`} data={data} unit={unit} onSelect={onSelect} selected={filters.municipality ?? filters.department} tone={tone} scaleMax={scaleMax} />
        <div className="territorial-map__source" style={{ borderTop: "1px solid var(--line)", paddingTop: 10, fontSize: 10, color: "var(--ink-500)" }}>
          Límites: <a href={data.source.url} target="_blank" rel="noreferrer" style={{ color: "var(--forest-700)" }}>DANE · MGN 2025</a> · Geometría simplificada · Datos EVA {filters.year}
        </div>
      </>}
    </article>
  );
}
