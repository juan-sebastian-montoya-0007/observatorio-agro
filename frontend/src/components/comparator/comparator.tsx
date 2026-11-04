"use client";

import { useEffect, useRef, useState } from 'react';
import { ArrowLeftRight, BarChart3, CalendarDays, Database, Download, FolderOpen, Gauge, MapPin, Save, Sprout, TrendingUp } from 'lucide-react';
import { EChart } from '@/components/common/echart';
import { InfoTooltip } from '@/components/common/info-tooltip';
import { TerritorialMap } from '@/components/dashboard/territorial-map';
import { getCatalogs, getDepartments, getMunicipalities } from '@/services/catalog';
import { runQuery, type Query, type QueryResult } from '@/services/advanced';
import type { AnalyticalEnvelope, Crop, Department, Municipality } from '@/types/api';
import type { Indicator } from '@/types/filters';
import { stability, variation } from './calculations';
import './comparator.css';

const metrics: Record<Indicator, string> = { planted_area_ha: 'Área sembrada', harvested_area_ha: 'Área cosechada', production_t: 'Producción', yield_t_ha: 'Rendimiento' };
const units: Record<Indicator, string> = { planted_area_ha: 'ha', harvested_area_ha: 'ha', production_t: 't', yield_t_ha: 't/ha' };
const keys = Object.keys(metrics) as Indicator[];
const modes = ['Territorios', 'Cultivos', 'Periodos', 'Contra referente', 'Escenarios'];
const views = ['Evolución histórica', 'Comparación territorial', 'Mapa comparativo', 'Productividad y brechas', 'Estabilidad', 'Escenarios', 'Evaluación multicriterio', 'Resumen y conclusiones'];
const base: Query = { year: 2025, yearFrom: 2019, periodMode: 'AGRICULTURAL_YEAR', indicator: 'production_t', dimension: 'municipality', orderBy: 'production_t', direction: 'desc', limit: 100, compareYear: 2019, compare: true, secondary: '', showVariation: true };
type Configuration = { mode: string; a: Query; b: Query };
type Results = { a: AnalyticalEnvelope<QueryResult>; b: AnalyticalEnvelope<QueryResult> };
const initial: Configuration = { mode: 'Territorios', a: { ...base, department: '41' }, b: { ...base, department: '73' } };
const num = (value: unknown, digits = 2) => value == null ? '—' : new Intl.NumberFormat('es-CO', { maximumFractionDigits: digits }).format(Number(value));
const pct = (value: number | null) => value === null ? 'Sin base comparable' : `${value > 0 ? '+' : ''}${num(value, 1)} %`;
const value = (result: QueryResult | undefined, metric: Indicator) => result?.summary?.[metric] == null ? null : Number(result.summary[metric]);
const unique = (items: string[]) => [...new Set(items)].filter(Boolean).sort((a, b) => a.localeCompare(b, 'es'));
const yearOptions = [2019, 2020, 2021, 2022, 2023, 2024, 2025];
const storage = 'observatorio-agro-comparaciones-v1';

function Alternative({ side, query, departments, crops, onChange, mode }: { side: string; query: Query; departments: Department[]; crops: Crop[]; onChange: (query: Query) => void; mode: string }) {
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    setMunicipalities([]); setError('');
    if (!query.department) return;
    const controller = new AbortController();
    getMunicipalities(query.department, controller.signal).then(response => setMunicipalities(response.data)).catch(() => { if (!controller.signal.aborted) setError('No se pudieron cargar los municipios.'); });
    return () => controller.abort();
  }, [query.department]);
  return <div className={`cmp-alternative cmp-alternative--${side.toLowerCase()}`}><h3><b>{side}</b>Alternativa {side}</h3><div className="cmp-fields">
    <label>Departamento<select aria-label={`Departamento ${side}`} disabled={mode === 'Contra referente' && side === 'B'} value={query.department ?? ''} onChange={event => onChange({ ...query, department: event.target.value || undefined, municipality: undefined })}><option value="">Colombia</option>{departments.map(item => <option value={item.code} key={item.code}>{item.name}</option>)}</select></label>
    <label>Municipios (opcional)<select aria-label={`Municipio ${side}`} disabled={!query.department} value={query.municipality ?? ''} onChange={event => onChange({ ...query, municipality: event.target.value || undefined })}><option value="">Todos los municipios</option>{municipalities.map(item => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label>
    {mode === 'Cultivos' && <label>Cultivo {side}<select aria-label={`Cultivo ${side}`} value={query.crop ?? ''} onChange={event => onChange({ ...query, crop: event.target.value ? Number(event.target.value) : undefined, cropVariant: undefined })}><option value="">Todos los cultivos</option>{crops.map(crop => <option key={crop.id} value={crop.id}>{crop.name}</option>)}</select></label>}
    {mode === 'Periodos' && <><label>Desde {side}<select aria-label={`Año inicial ${side}`} value={query.yearFrom} onChange={event => onChange({ ...query, yearFrom: Number(event.target.value), compareYear: Number(event.target.value) })}>{yearOptions.filter(year => year <= query.year).map(year => <option key={year}>{year}</option>)}</select></label><label>Hasta {side}<select aria-label={`Año final ${side}`} value={query.year} onChange={event => onChange({ ...query, year: Number(event.target.value) })}>{yearOptions.filter(year => year >= query.yearFrom).map(year => <option key={year}>{year}</option>)}</select></label></>}
  </div>{error && <p role="alert">{error}</p>}</div>;
}

export function Comparator() {
  const [draft, setDraft] = useState<Configuration>(initial);
  const [applied, setApplied] = useState<Configuration>(initial);
  const [results, setResults] = useState<Results | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [crops, setCrops] = useState<Crop[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [view, setView] = useState(views[0]);
  const [metric, setMetric] = useState<Indicator>('production_t');
  const [relative, setRelative] = useState(false);
  const [gapSide, setGapSide] = useState<'a' | 'b'>('a');
  const [improvement, setImprovement] = useState(20);
  const [weights, setWeights] = useState([40, 30, 30]);
  const [saved, setSaved] = useState<{ name: string; configuration: Configuration }[]>([]);
  const [notice, setNotice] = useState('');
  const request = useRef<AbortController | null>(null);
  async function compare(configuration: Configuration) {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setBusy(true); setError('');
    try {
      const [a, b] = await Promise.all([runQuery(configuration.a, controller.signal), runQuery(configuration.b, controller.signal)]);
      if (controller.signal.aborted) return;
      setResults({ a, b }); setApplied(configuration);
    } catch { if (!controller.signal.aborted) setError('No se pudo cargar la comparación. Revisa los filtros y vuelve a comparar.'); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  useEffect(() => {
    let active = true;
    Promise.all([getDepartments(), getCatalogs()]).then(([territories, catalog]) => {
      if (!active) return;
      setDepartments(territories.data); setCrops(catalog.crops.data);
      const crop = catalog.crops.data.find(item => item.name.toLowerCase() === 'cacao')?.id;
      const config = { ...initial, a: { ...initial.a, crop }, b: { ...initial.b, crop } }; setDraft(config); void compare(config);
    }).catch(() => { if (active) { setError('No se pudieron cargar los catálogos. Recarga la página.'); setBusy(false); } });
    try { const stored = JSON.parse(localStorage.getItem(storage) ?? '[]'); if (Array.isArray(stored)) setSaved(stored.filter(item => typeof item?.name === 'string' && item.configuration?.a?.year && item.configuration?.b?.year).slice(0, 20)); } catch { /* Storage is optional. */ }
    return () => { active = false; request.current?.abort(); };
  }, []);
  const both = (changes: Partial<Query>) => setDraft(current => ({ ...current, a: { ...current.a, ...changes }, b: { ...current.b, ...changes } }));
  const modeChange = (mode: string) => {
    setDraft(current => ({ ...current, mode, b: mode === 'Contra referente' ? { ...current.a, department: undefined, municipality: undefined } : mode === 'Periodos' ? { ...current.a, year: Math.max(current.a.yearFrom, current.a.year - 1) } : mode === 'Cultivos' ? { ...current.a, crop: current.b.crop, cropVariant: undefined } : current.b }));
    if (mode === 'Escenarios') setView('Escenarios');
  };
  function updateSide(side: 'a' | 'b', query: Query) {
    setDraft(current => {
      const next = { ...current, [side]: query };
      if (side === 'a' && current.mode === 'Contra referente') next.b = { ...query, department: undefined, municipality: undefined };
      return next;
    });
  }
  const data = { a: results?.a.data, b: results?.b.data };
  const territory = (query: Query) => query.municipality ? `${departments.find(item => item.code === query.department)?.name ?? ''} · ${query.municipality}` : departments.find(item => item.code === query.department)?.name ?? 'Colombia';
  const label = (side: 'a' | 'b') => `${territory(applied[side])}${applied.mode === 'Cultivos' ? ` · ${crops.find(crop => crop.id === applied[side].crop)?.name ?? 'Todos'}` : ''}${applied.mode === 'Periodos' ? ` · ${applied[side].year}` : ''}`;
  const allYears = [...new Set([...(data.a?.series ?? []), ...(data.b?.series ?? [])].map(point => point.year))].sort();
  // Each section belongs only to its primary tab, never to a catch-all view.
  const visible = (primaryTab: string, ..._relatedTabs: string[]) => view === primaryTab;
  const seriesOption = {
    color: ['#087b50', '#367aff'], tooltip: { trigger: 'axis' }, legend: { top: 0, right: 4, textStyle: { fontSize: 9 } },
    grid: { left: 60, right: 14, bottom: 37, top: 28 },
    xAxis: { type: 'category', data: allYears, name: 'Año', nameLocation: 'middle', nameGap: 24, axisLabel: { fontSize: 9 } },
    yAxis: { type: 'value', name: `${metrics[metric]} (${units[metric]})`, nameLocation: 'middle', nameGap: 45, nameTextStyle: { fontSize: 9 }, axisLabel: { fontSize: 8, formatter: (value: number) => new Intl.NumberFormat('es', { notation: 'compact' }).format(value) }, splitLine: { lineStyle: { color: '#edf2f3' } } },
    series: (['a', 'b'] as const).map(side => ({ name: `${side.toUpperCase()} · ${label(side)}`, type: 'line', smooth: .15, connectNulls: false, symbolSize: 5, areaStyle: { opacity: .09 }, data: allYears.map(year => data[side]?.series.find(point => point.year === year)?.[metric] ?? null) })),
  };
  const scatter = { color: ['#087b50', '#367aff'], tooltip: { trigger: 'item', formatter: (item: { data: [number, number, string] }) => `${item.data[2].replace(/[<>&]/g, '')}<br/>Área cosechada: ${num(item.data[0])} ha<br/>Rendimiento: ${num(item.data[1])} t/ha` }, legend: { top: 0, textStyle: { fontSize: 9 } }, grid: { left: 50, right: 20, top: 30, bottom: 45 }, xAxis: { type: 'log', name: 'Área cosechada (ha) · escala logarítmica', nameLocation: 'middle', nameGap: 28, nameTextStyle: { fontSize: 9 }, axisLabel: { fontSize: 8 } }, yAxis: { type: 'value', name: 'Rendimiento (t/ha)', nameLocation: 'middle', nameGap: 33, nameTextStyle: { fontSize: 9 }, axisLabel: { fontSize: 8 }, splitLine: { lineStyle: { color: '#edf2f3' } } }, series: (['a', 'b'] as const).map(side => ({ name: `${side.toUpperCase()} · ${label(side)}`, type: 'scatter', symbolSize: 5, data: (data[side]?.municipalities ?? []).filter(row => row.harvested_area_ha !== null && row.harvested_area_ha > 0 && row.yield_t_ha !== null).map(row => [row.harvested_area_ha, row.yield_t_ha, row.name]) })) };
  const gapReference = value(data[gapSide], 'yield_t_ha');
  const gaps = (data[gapSide]?.municipalities ?? []).filter(row => row.yield_t_ha !== null).slice(0, 12).map(row => ({ name: row.name, gap: variation(gapReference, row.yield_t_ha) }));
  const gapChart = { grid: { left: 44, right: 10, top: 20, bottom: 52 }, tooltip: { trigger: 'axis' }, xAxis: { type: 'category', name: 'Municipio', nameLocation: 'middle', nameGap: 38, nameTextStyle: { fontSize: 8 }, data: gaps.map(row => row.name), axisLabel: { fontSize: 7, rotate: 25, width: 45, overflow: 'truncate' } }, yAxis: { type: 'value', name: 'Brecha (%)', nameLocation: 'middle', nameGap: 30, nameTextStyle: { fontSize: 8 }, axisLabel: { fontSize: 8 } }, series: [{ type: 'bar', data: gaps.map(row => ({ value: row.gap, itemStyle: { color: (row.gap ?? 0) < 0 ? '#ef7474' : '#329e72' } })) }] };
  const stabilityA = stability(data.a?.series ?? [], metric), stabilityB = stability(data.b?.series ?? [], metric);
  const scaleMax = Math.max(0, ...(['a', 'b'] as const).flatMap(side => (data[side]?.municipalities ?? []).map(row => row[metric] ?? 0)));
  const currentProduction = value(data.a, 'production_t');
  const projected = currentProduction === null ? null : currentProduction * (1 + improvement / 100);
  const scoreKeys: Indicator[] = ['production_t', 'harvested_area_ha', 'yield_t_ha'];
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
  const score = (side: 'a' | 'b') => totalWeight === 0 || scoreKeys.some(key => value(data.a, key) === null || value(data.b, key) === null) ? null : scoreKeys.reduce((sum, key, index) => { const maximum = Math.max(value(data.a, key) ?? 0, value(data.b, key) ?? 0); return sum + (maximum > 0 ? (value(data[side], key) ?? 0) / maximum : 0) * weights[index] / totalWeight * 100; }, 0);
  function save() {
    const next = [{ name: `${label('a')} vs ${label('b')} · ${new Date().toLocaleTimeString('es-CO')}`, configuration: applied }, ...saved].slice(0, 20);
    try { localStorage.setItem(storage, JSON.stringify(next)); setSaved(next); setNotice('Comparación guardada en este navegador.'); } catch { setNotice('El navegador no permite guardar la comparación.'); }
  }
  function exportCsv() {
    if (!results) return;
    const rows = [['Alternativa', 'Territorio', 'Año', 'Periodo', ...keys.map(key => `${metrics[key]} (${units[key]})`), 'Fuente'], ...(['a', 'b'] as const).flatMap(side => results[side].data.series.map(point => [side.toUpperCase(), label(side), point.year, point.period_type, ...keys.map(key => point[key]), 'EVA - UPRA']))];
    const escape = (cell: unknown) => `"${String(cell ?? '').replace(/^[=+@-]/, "'").replaceAll('"', '""')}"`;
    const url = URL.createObjectURL(new Blob(['\uFEFF' + rows.map(row => row.map(escape).join(';')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'comparacion-agro.csv'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className="comparator">
    <header className="cmp-hero"><div><span>ANÁLISIS COMPARATIVO</span><h1>Comparador agropecuario</h1><p>Compara territorios, cultivos y periodos para tomar mejores decisiones.</p></div><div className="cmp-context"><span><Sprout /><span>Cultivo<strong>{crops.find(crop => crop.id === applied.a.crop)?.name ?? 'Todos los cultivos'}</strong></span></span><span><CalendarDays /><span>Periodo<strong>{applied.a.yearFrom}–{applied.a.year}</strong></span></span><span><MapPin /><span>Territorios<strong>{territory(applied.a)} vs. {territory(applied.b)}</strong></span></span><span><Database /><span>Fuente<strong>EVA · UPRA</strong></span></span></div></header>
    <section className="cmp-card cmp-configuration"><header><h2><SlidersIcon />1. Configure su comparación</h2><div className="cmp-tabs" role="group" aria-label="Tipo de comparación">{modes.map(mode => <button key={mode} className={draft.mode === mode ? 'active' : ''} aria-pressed={draft.mode === mode} onClick={() => modeChange(mode)}>{mode}</button>)}</div><div className="cmp-save"><label><FolderOpen /><select aria-label="Cargar comparación" value="" onChange={event => { const item = saved[Number(event.target.value)]; if (item) { setDraft(item.configuration); void compare(item.configuration); } }}><option value="">Cargar comparación</option>{saved.map((item, index) => <option key={index} value={index}>{item.name}</option>)}</select></label><button disabled={!results || busy} onClick={save}><Save />Guardar comparación</button></div></header>
      <div className="cmp-config-grid"><Alternative side="A" query={draft.a} departments={departments} crops={crops} mode={draft.mode} onChange={query => updateSide('a', query)} /><div className="cmp-common"><label>Cultivo{draft.mode === 'Cultivos' ? <small>Selecciona un cultivo en cada alternativa.</small> : <select aria-label="Cultivo común" value={draft.a.crop ?? ''} onChange={event => both({ crop: event.target.value ? Number(event.target.value) : undefined, cropVariant: undefined })}><option value="">Todos los cultivos</option>{crops.map(crop => <option key={crop.id} value={crop.id}>{crop.name}</option>)}</select>}</label><label>Periodo<div className="cmp-years"><select aria-label="Desde" disabled={draft.mode === 'Periodos'} value={draft.a.yearFrom} onChange={event => both({ yearFrom: Number(event.target.value), compareYear: Number(event.target.value) })}>{yearOptions.filter(year => year <= draft.a.year).map(year => <option key={year}>{year}</option>)}</select><span>–</span><select aria-label="Hasta" disabled={draft.mode === 'Periodos'} value={draft.a.year} onChange={event => both({ year: Number(event.target.value) })}>{yearOptions.filter(year => year >= draft.a.yearFrom).map(year => <option key={year}>{year}</option>)}</select></div></label></div><Alternative side="B" query={draft.b} departments={departments} crops={crops} mode={draft.mode} onChange={query => updateSide('b', query)} /><button className="cmp-run" disabled={busy} onClick={() => void compare(draft)}><ArrowLeftRight />{busy ? 'Consultando…' : 'Comparar'}</button></div>
      <details className="cmp-more"><summary>Más filtros: grupo, subgrupo, tipo, clasificación y periodo de la fuente</summary><div>{(['a', 'b'] as const).map(side => <fieldset key={side}><legend>Alternativa {side.toUpperCase()}</legend>{(['group', 'subgroup', 'cycle', 'classification'] as const).map((key, index) => <label key={key}>{['Grupo', 'Subgrupo', 'Tipo de cultivo', 'Clasificación'][index]}<select value={draft[side][key] ?? ''} onChange={event => updateSide(side, { ...draft[side], [key]: event.target.value || undefined, crop: undefined, cropVariant: undefined })}><option value="">Todos</option>{unique(crops.map(crop => key === 'classification' ? crop.general_classification : crop[key])).map(item => <option key={item}>{item}</option>)}</select></label>)}<label>Variedad / desagregación<select disabled={!draft[side].crop} value={draft[side].cropVariant ?? ''} onChange={event => updateSide(side, { ...draft[side], cropVariant: event.target.value ? Number(event.target.value) : undefined })}><option value="">Todas</option>{crops.find(crop => crop.id === draft[side].crop)?.variants.map(variant => <option key={variant.id} value={variant.id}>{variant.disaggregation || variant.scientific_name || variant.source_code}</option>)}</select></label><label>Lectura temporal<select value={draft[side].periodMode === 'AGRICULTURAL_YEAR' ? 'AGRICULTURAL_YEAR' : draft[side].periodType ?? 'ANNUAL'} onChange={event => updateSide(side, { ...draft[side], periodMode: event.target.value === 'AGRICULTURAL_YEAR' ? 'AGRICULTURAL_YEAR' : 'SOURCE', periodType: event.target.value === 'AGRICULTURAL_YEAR' ? undefined : event.target.value as Query['periodType'] })}><option value="AGRICULTURAL_YEAR">Año agrícola</option><option value="ANNUAL">Anual de fuente</option><option value="SEMESTER_A">Semestre A</option><option value="SEMESTER_B">Semestre B</option></select></label></fieldset>)}</div></details>
      {JSON.stringify(draft) !== JSON.stringify(applied) && <p className="cmp-note">Hay cambios sin aplicar. Pulsa Comparar.</p>}{error && <p role="alert" className="cmp-error">{error}</p>}{notice && <p role="status" className="cmp-note">{notice}</p>}
    </section>
    {results && <><div className="cmp-kpis">{(['harvested_area_ha', 'production_t', 'yield_t_ha', 'share'] as const).map((key, index) => <article className="cmp-card cmp-kpi" key={key}><span className={`cmp-kpi-icon cmp-kpi-icon--${index}`}>{index === 0 ? <Sprout /> : index === 1 ? <BarChart3 /> : index === 2 ? <Gauge /> : <Database />}</span><div><h3>{key === 'share' ? 'Participación nacional' : metrics[key]} <small>{applied.a.year === applied.b.year ? applied.a.year : `${applied.a.year} / ${applied.b.year}`}</small></h3><div className="cmp-kpi-values">{(['a', 'b'] as const).map(side => { const national = data[side]?.national_summary?.production_t; const share = national != null && Number(national) > 0 && value(data[side], 'production_t') !== null ? value(data[side], 'production_t')! / Number(national) * 100 : null; const first = data[side]?.series.find(point => point.year === applied[side].yearFrom); return <div key={side}><strong><b className={`cmp-badge ${side}`}>{side.toUpperCase()}</b>{key === 'share' ? `${num(share, 1)} %` : `${num(value(data[side], key))} ${units[key]}`}</strong><small>{key === 'share' ? 'del mismo cultivo y filtros en Colombia' : `${pct(variation(first?.[key] == null ? null : Number(first[key]), value(data[side], key)))} vs ${applied[side].yearFrom}`}</small></div>; })}</div></div></article>)}</div>
    <nav className="cmp-view-tabs" aria-label="Vistas del comparador">{views.map((name, index) => <button key={name} className={view === name ? 'active' : ''} aria-pressed={view === name} onClick={() => setView(name)}>{index === 0 ? <TrendingUp /> : index === 2 ? <MapPin /> : <BarChart3 />}{name}</button>)}</nav>
    <div className="cmp-toolbar"><label>Indicador de análisis<select value={metric} onChange={event => setMetric(event.target.value as Indicator)}>{keys.map(key => <option key={key} value={key}>{metrics[key]} ({units[key]})</option>)}</select></label><span>A: {label('a')} · B: {label('b')}</span><button onClick={exportCsv}><Download />Exportar series CSV</button></div>
    <div className="cmp-grid">
      {visible('Evolución histórica') && <article className="cmp-card cmp-history"><h2>Evolución de {metrics[metric].toLowerCase()}</h2><EChart option={seriesOption} ariaLabel={`Evolución histórica. Eje X: Año; eje Y: ${metrics[metric]} (${units[metric]})`} items={allYears.map(year => ({ label: String(year), value: (['a', 'b'] as const).map(side => `${side.toUpperCase()}: ${num(data[side]?.series.find(point => point.year === year)?.[metric])} ${units[metric]}`).join(' · ') }))} /></article>}
      {visible('Comparación territorial', 'Evaluación multicriterio') && <article className="cmp-card cmp-indicator-chart"><header><h2>Comparación de indicadores ({applied.a.year} / {applied.b.year})</h2><select aria-label="Escala de indicadores" value={relative ? 'relative' : 'absolute'} onChange={event => setRelative(event.target.value === 'relative')}><option value="absolute">Valores absolutos</option><option value="relative">Mayor valor = 100</option></select></header><div className="cmp-four-charts">{keys.map(key => { const vals = [value(data.a, key), value(data.b, key)]; const max = Math.max(0, ...vals.map(v => v ?? 0)); return <div key={key}><EChart ariaLabel={`${metrics[key]} de A y B; eje vertical ${relative ? 'Índice relativo' : units[key]}`} option={{ grid: { left: 32, right: 8, top: 20, bottom: 23 }, tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: ['A', 'B'], axisLabel: { fontSize: 9 } }, yAxis: { type: 'value', name: relative ? 'Índice' : units[key], nameTextStyle: { fontSize: 8 }, axisLabel: { fontSize: 7, formatter: (v: number) => new Intl.NumberFormat('es', { notation: 'compact' }).format(v) }, splitLine: { lineStyle: { color: '#edf2f3' } } }, series: [{ type: 'bar', barMaxWidth: 28, data: vals.map((v, i) => ({ value: v === null ? null : relative ? max > 0 ? v / max * 100 : 0 : v, itemStyle: { color: i ? '#367aff' : '#087b50' } })) }] }} items={vals.map((v, i) => ({ label: i ? 'B' : 'A', value: `${num(v)} ${units[key]}` }))} /><h3>{metrics[key]}</h3></div>; })}</div><p className="cmp-note">Cada indicador usa su propia escala y unidad.</p></article>}
      {visible('Mapa comparativo', 'Comparación territorial') && <article className="cmp-card cmp-maps"><h2>Distribución territorial de {metrics[metric].toLowerCase()}</h2><div>{(['a', 'b'] as const).map(side => <section key={side} className={`cmp-map-side ${side}`}><h3><b className={`cmp-badge ${side}`}>{side.toUpperCase()}</b>{label(side)} · {applied[side].year}</h3><div className="cmp-map-content"><TerritorialMap filters={{ ...applied[side], indicator: metric, yearFrom: applied[side].year }} tone={side === 'a' ? 'green' : 'blue'} scaleMax={scaleMax} /><ol>{[...(data[side]?.municipalities ?? [])].filter(row => row[metric] !== null).sort((a, b) => (b[metric] ?? 0) - (a[metric] ?? 0)).slice(0, 5).map(row => <li key={row.id}><span>{row.name}</span><strong>{num(row[metric])} {units[metric]}</strong></li>)}</ol></div></section>)}</div></article>}
      {visible('Productividad y brechas') && <article className="cmp-card cmp-scatter"><h2>Matriz de productividad</h2><EChart option={scatter} ariaLabel="Municipios: área cosechada (ha) en eje X logarítmico y rendimiento (t/ha) en eje Y" items={(['a', 'b'] as const).flatMap(side => (data[side]?.municipalities ?? []).map(row => ({ label: `${side.toUpperCase()} · ${row.name}`, value: `${num(row.harvested_area_ha)} ha · ${num(row.yield_t_ha)} t/ha` })))} /><p className="cmp-note">Todos los municipios con área cosechada mayor que cero y rendimiento disponible.</p></article>}
      {visible('Productividad y brechas') && <article className="cmp-card cmp-gaps"><h2>Brechas de productividad <InfoTooltip label="Cálculo de la brecha" content="(Rendimiento municipal / rendimiento agregado del territorio − 1) × 100. No representa área pendiente de cosecha." /></h2><div className="cmp-tabs">{(['a', 'b'] as const).map(side => <button key={side} className={gapSide === side ? 'active' : ''} onClick={() => setGapSide(side)}>{side.toUpperCase()} · {label(side)}</button>)}</div><EChart option={gapChart} ariaLabel="Brecha porcentual de rendimiento municipal frente al territorio seleccionado" items={gaps.map(row => ({ label: row.name, value: pct(row.gap) }))} /><p className="cmp-note">Hasta 12 municipios, ordenados por rendimiento.</p></article>}
      {visible('Estabilidad') && <article className="cmp-card cmp-stability"><h2>Estabilidad de {metrics[metric].toLowerCase()} <InfoTooltip label="Método de estabilidad" content="Estadísticas de cambios porcentuales entre años consecutivos del rango seleccionado. Se excluyen bases cero o ausentes. Desviación poblacional, expresada en puntos porcentuales." /></h2><table><thead><tr><th>Indicador</th><th>A</th><th>B</th></tr></thead><tbody>{[['Crecimiento promedio anual', pct(stabilityA.average), pct(stabilityB.average)], ['Años de aumento', `${stabilityA.increases} de ${stabilityA.count}`, `${stabilityB.increases} de ${stabilityB.count}`], ['Desviación estándar (p.p.)', num(stabilityA.deviation), num(stabilityB.deviation)], ['Variación máxima anual', pct(stabilityA.max), pct(stabilityB.max)], ['Variación mínima anual', pct(stabilityA.min), pct(stabilityB.min)]].map(row => <tr key={row[0]}>{row.map((cell, index) => <td key={index}>{cell}</td>)}</tr>)}</tbody></table></article>}
      {visible('Escenarios') && <article className="cmp-card cmp-scenario"><h2>Simulador de escenarios <InfoTooltip label="Supuestos del escenario" content="Producción estimada = producción actual de A × (1 + mejora de rendimiento / 100), manteniendo el área cosechada constante. No es una predicción ni incluye costos o clima." /></h2><label>Mejora del rendimiento de A (%)<div><input aria-label="Mejora del rendimiento" type="range" min="-50" max="100" value={improvement} onChange={event => setImprovement(Number(event.target.value))} /><output>{improvement}%</output></div></label><div className="cmp-projection"><div><span>Producción actual</span><strong>{num(currentProduction)} t</strong></div><div><span>Producción estimada</span><strong>{num(projected)} t</strong><small>{num(projected === null || currentProduction === null ? null : projected - currentProduction)} t de diferencia</small></div></div><p className="cmp-note">Escenario hipotético para {label('a')} ({applied.a.year}), no una predicción.</p></article>}
      {view === 'Evaluación multicriterio' && <article className="cmp-card cmp-wide"><h2>Evaluación multicriterio transparente</h2><p>Pondera área cosechada, producción y rendimiento. Cada criterio se normaliza frente al mayor valor de las dos alternativas. No es una recomendación de inversión.</p><div className="cmp-weights">{scoreKeys.map((key, index) => <label key={key}>{metrics[key]} · peso {weights[index]}<input type="range" min="0" max="100" value={weights[index]} onChange={event => setWeights(current => current.map((weight, i) => i === index ? Number(event.target.value) : weight))} /></label>)}</div><div className="cmp-score"><strong>A: {num(score('a'), 1)} / 100</strong><strong>B: {num(score('b'), 1)} / 100</strong></div>{totalWeight === 0 && <p role="alert">Asigna un peso mayor que cero para calcular.</p>}</article>}
      {view === 'Resumen y conclusiones' && <article className="cmp-card cmp-wide"><h2>Resumen de la comparación</h2><table><thead><tr><th>Indicador</th><th>A · {label('a')} · {applied.a.year}</th><th>B · {label('b')} · {applied.b.year}</th><th>A respecto a B</th></tr></thead><tbody>{keys.map(key => <tr key={key}><td>{metrics[key]} ({units[key]})</td><td>{num(value(data.a, key))}</td><td>{num(value(data.b, key))}</td><td>{pct(variation(value(data.b, key), value(data.a, key)))}</td></tr>)}</tbody></table><p>La producción de A presenta una diferencia de {pct(variation(value(data.b, 'production_t'), value(data.a, 'production_t')))} frente a B. La diferencia de rendimiento es {pct(variation(value(data.b, 'yield_t_ha'), value(data.a, 'yield_t_ha')))}.</p><p>Las diferencias describen los registros consultados; no demuestran causalidad ni rentabilidad. Compara cultivos y lecturas temporales equivalentes para una interpretación consistente.</p></article>}
    </div><footer className="cmp-methodology">Datos obtenidos de EVA · UPRA. {unique([...results.a.methodology, ...results.b.methodology, ...results.a.warnings.map(item => item.message), ...results.b.warnings.map(item => item.message)]).join(' ')} La participación nacional usa el mismo cultivo, periodo y filtros productivos de cada alternativa.</footer></>}
    {!busy && results && (!data.a?.summary || !data.b?.summary) && <p role="status" className="cmp-error">Una alternativa no tiene datos para los filtros seleccionados. Los valores ausentes se muestran como —, no como cero.</p>}
    {busy && !results && <p role="status" className="cmp-loading">Cargando comparación y cartografía…</p>}
  </section>;
}

function SlidersIcon() { return <ArrowLeftRight size={14} />; }
