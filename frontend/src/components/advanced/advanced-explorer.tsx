"use client";

import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, BarChart3, CalendarDays, ChevronLeft, ChevronRight, Database, Download, FolderOpen, MapPin, Save, Search, SlidersHorizontal, Sprout } from 'lucide-react';
import { EChart } from '@/components/common/echart';
import { TerritorialMap } from '@/components/dashboard/territorial-map';
import { InfoTooltip } from '@/components/common/info-tooltip';
import { getCatalogs, getDepartments, getMunicipalities } from '@/services/catalog';
import { runQuery, type Query, type QueryResult } from '@/services/advanced';
import type { AnalyticalEnvelope, Crop, Department, Municipality } from '@/types/api';
import type { Indicator } from '@/types/filters';
import './advanced.css';

const metrics: Record<Indicator, string> = { production_t: 'Producción (t)', planted_area_ha: 'Área sembrada (ha)', harvested_area_ha: 'Área cosechada (ha)', yield_t_ha: 'Rendimiento (t/ha)' };
const dimensions = { municipality: 'Municipio', department: 'Departamento', year: 'Año', crop: 'Cultivo' } as const;
const defaults: Query = { year: 2025, yearFrom: 2019, department: '41', periodMode: 'AGRICULTURAL_YEAR', indicator: 'production_t', dimension: 'municipality', orderBy: 'production_t', direction: 'desc', limit: 20, compareYear: 2024, compare: false, secondary: 'yield_t_ha', showVariation: true };
const number = (value: number | string | null | undefined, digits = 2) => value == null ? '—' : new Intl.NumberFormat('es-CO', { maximumFractionDigits: digits }).format(Number(value));
const years = [2019, 2020, 2021, 2022, 2023, 2024, 2025];
const unique = (values: string[]) => [...new Set(values)].filter(Boolean).sort((a, b) => a.localeCompare(b, 'es'));
const storageKey = 'observatorio-agro-consultas-v1';

function MetricOptions() { return <>{Object.entries(metrics).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</>; }

export function AdvancedExplorer() {
  const [draft, setDraft] = useState<Query>(defaults);
  const [applied, setApplied] = useState<Query>(defaults);
  const [response, setResponse] = useState<AnalyticalEnvelope<QueryResult> | null>(null);
  const [crops, setCrops] = useState<Crop[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [search, setSearch] = useState('');
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [view, setView] = useState('Tabla');
  const [filterTab, setFilterTab] = useState('Territorio');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [chartType, setChartType] = useState('line');
  const [saved, setSaved] = useState<{ name: string; query: Query }[]>([]);
  const request = useRef<AbortController | null>(null);

  function change<K extends keyof Query>(key: K, value: Query[K]) { setDraft(previous => ({ ...previous, [key]: value })); }
  async function execute(query: Query) {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setError('');
    try { const result = await runQuery(query, controller.signal); if (controller.signal.aborted) return; setResponse(result); setApplied({ ...query }); setPage(1); }
    catch (cause) { if (!controller.signal.aborted) setError('No se pudo ejecutar la consulta. Revisa los filtros e inténtalo de nuevo.'); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  useEffect(() => {
    let active = true;
    Promise.all([getCatalogs(), getDepartments()]).then(([catalogs, territories]) => {
      if (!active) return;
      setCrops(catalogs.crops.data); setDepartments(territories.data);
      const cacao = catalogs.crops.data.find(crop => crop.name.toLocaleLowerCase('es') === 'cacao');
      const initial = { ...defaults, crop: cacao?.id }; setDraft(initial); void execute(initial);
    }).catch(() => { if (active) { setError('No se pudieron cargar los filtros. Recarga la página para reintentar.'); setBusy(false); } });
    try { const stored: unknown = JSON.parse(localStorage.getItem(storageKey) ?? '[]'); if (Array.isArray(stored)) setSaved(stored.filter(item => item && typeof item.name === 'string' && item.query?.year >= 2019 && item.query?.year <= 2025).slice(0, 20)); } catch { /* Storage is optional. */ }
    return () => { active = false; request.current?.abort(); };
  }, []);
  useEffect(() => {
    setMunicipalities([]);
    if (!draft.department) return;
    const controller = new AbortController();
    getMunicipalities(draft.department, controller.signal).then(result => setMunicipalities(result.data)).catch(() => {});
    return () => controller.abort();
  }, [draft.department]);

  const result = response?.data;
  const dirty = JSON.stringify(draft) !== JSON.stringify(applied);
  const filteredCrops = crops.filter(crop => (!draft.group || crop.group === draft.group) && (!draft.subgroup || crop.subgroup === draft.subgroup) && (!draft.classification || crop.general_classification === draft.classification) && (!draft.cycle || crop.cycle === draft.cycle));
  const place = departments.find(department => department.code === applied.department)?.name ?? 'Colombia';
  const pages = Math.max(1, Math.ceil((result?.rows.length ?? 0) / pageSize));
  const rows = result?.rows.slice((page - 1) * pageSize, page * pageSize) ?? [];
  const graph = {
    color: ['#087b50', '#85bd6a', '#ca9f43'], tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { fontSize: 9 }, itemWidth: 10 },
    grid: { left: 55, right: applied.secondary ? 55 : 15, bottom: 40, top: 35 },
    xAxis: { type: 'category', name: 'Año', nameLocation: 'middle', nameGap: 25, axisLabel: { fontSize: 9 }, data: result?.series.map(point => point.year) ?? [] },
    yAxis: [{ type: 'value', name: metrics[applied.indicator], nameLocation: 'middle', nameGap: 40, nameTextStyle: { fontSize: 8 }, axisLabel: { fontSize: 8, formatter: (value: number) => new Intl.NumberFormat('es', { notation: 'compact' }).format(value) }, splitLine: { lineStyle: { color: '#edf1ef' } } }, ...(applied.secondary ? [{ type: 'value', name: metrics[applied.secondary], nameLocation: 'middle', nameGap: 33, nameTextStyle: { fontSize: 8 }, axisLabel: { fontSize: 8 }, splitLine: { show: false } }] : [])],
    series: [{ name: place, type: chartType, data: result?.series.map(point => point[applied.indicator]), smooth: .2, areaStyle: chartType === 'line' ? { opacity: .09 } : undefined }, { name: 'Colombia', type: chartType, data: result?.national_series.map(point => point[applied.indicator]), smooth: .2 }, ...(applied.secondary ? [{ name: metrics[applied.secondary], type: 'line', yAxisIndex: 1, data: result?.series.map(point => point[applied.secondary as Indicator]), smooth: .2, lineStyle: { type: 'dashed' } }] : [])],
  };
  const compositionMetric = applied.indicator === 'yield_t_ha' ? 'harvested_area_ha' : applied.indicator;
  const composition = { color: ['#087751', '#89bf58', '#dfc786', '#8ba6a2'], tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' }, legend: { orient: 'vertical', right: 0, top: 'middle', itemWidth: 6, itemHeight: 6, textStyle: { fontSize: 8, width: 90, overflow: 'truncate' } }, series: [{ type: 'pie', radius: ['49%', '74%'], center: ['27%', '50%'], label: { show: false }, data: result?.composition.map(item => ({ name: item.name, value: item[compositionMetric] })) ?? [] }] };
  function save() {
    const entry = { name: `${place} · ${crops.find(crop => crop.id === applied.crop)?.name ?? 'Todos'} · ${applied.year} · ${new Date().toLocaleTimeString('es-CO')}`, query: applied };
    const next = [entry, ...saved].slice(0, 20);
    try { localStorage.setItem(storageKey, JSON.stringify(next)); setSaved(next); setNotice('Consulta guardada en este navegador.'); } catch { setNotice('El navegador no permite guardar consultas.'); }
  }
  function exportCsv() {
    if (!result) return;
    const cell = (value: unknown) => `"${String(value ?? '').replace(/^[=+@-]/, "'").replaceAll('"', '""')}"`;
    const lines = [[dimensions[applied.dimension], 'Departamento', ...Object.values(metrics), `Variación ${applied.compareYear}-${applied.year} (%)`], ...result.rows.map(row => [row.name, row.department, row.production_t, row.planted_area_ha, row.harvested_area_ha, row.yield_t_ha, row.variation])];
    const url = URL.createObjectURL(new Blob(['\uFEFF' + lines.map(line => line.map(cell).join(';')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `consulta-agro-${applied.year}.csv`; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const metricSelect = (value: Indicator, onChange: (value: Indicator) => void, label: string) => <select aria-label={label} value={value} onChange={event => onChange(event.target.value as Indicator)}><MetricOptions /></select>;

  return <section className="advanced">
    <header className="advanced-hero"><div><span>EXPLORACIÓN DE DATOS</span><h1>Consultas avanzadas</h1><p>Analiza, compara y explora la información agropecuaria de Colombia.</p></div><div className="advanced-hero__context"><span><MapPin />Colombia</span><span><CalendarDays /><span>{draft.yearFrom} - {draft.year}<small>Años disponibles</small></span></span><span><Database /><span>Datos EVA · UPRA<small>Base Agrícola Municipal</small></span></span></div></header>
    <div className="advanced-layout">
      <aside className="aq-card aq-territory" id="aq-territory"><h2><SlidersHorizontal />1. Filtros de consulta <button className="aq-clear" onClick={() => { setDraft({ ...defaults, department: undefined }); setSearch(''); }}>Limpiar todo</button></h2>
        <div className="aq-tabs" role="tablist" aria-label="Secciones de filtros">{['Territorio', 'Cultivos', 'Temporalidad', 'Indicadores'].map(name => <button type="button" role="tab" id={`filter-tab-${name}`} aria-selected={filterTab === name} aria-controls="aq-filter-panel" className={filterTab === name ? 'active' : ''} key={name} onClick={() => setFilterTab(name)}>{name}</button>)}</div>
        <div id="aq-filter-panel" role="tabpanel" aria-labelledby={`filter-tab-${filterTab}`}>
        {filterTab === 'Territorio' && <>
        <label>Departamento<select value={draft.department ?? ''} onChange={event => setDraft({ ...draft, department: event.target.value || undefined, municipality: undefined })}><option value="">Todo Colombia</option>{departments.map(item => <option value={item.code} key={item.code}>{item.name}</option>)}</select></label>
        <label>Municipios<select disabled={!draft.department} value={draft.municipality ?? ''} onChange={event => change('municipality', event.target.value || undefined)}><option value="">Todos los municipios</option>{municipalities.map(item => <option value={item.code} key={item.code}>{item.name}</option>)}</select></label>
        <div className="aq-search"><Search size={13} /><input aria-label="Buscar departamentos" placeholder="Buscar departamentos…" value={search} onChange={event => setSearch(event.target.value)} /></div>
        <div className="aq-territory-list" role="group" aria-label="Selección de departamento"><label><input type="checkbox" checked={!draft.department} onChange={() => setDraft({ ...draft, department: undefined, municipality: undefined })} />Todo Colombia</label>{departments.filter(item => item.name.toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g, '').includes(search.toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g, ''))).map(item => <label key={item.code} className={draft.department === item.code ? 'selected' : ''}><input type="checkbox" checked={draft.department === item.code} onChange={() => setDraft({ ...draft, department: draft.department === item.code ? undefined : item.code, municipality: undefined })} />{item.name}</label>)}</div>
        </>}
        {filterTab === 'Cultivos' && <>
          <label>Grupo de cultivo<select value={draft.group ?? ''} onChange={event => setDraft({ ...draft, group: event.target.value || undefined, subgroup: undefined, crop: undefined })}><option value="">Todos los grupos</option>{unique(crops.map(crop => crop.group)).map(item => <option key={item}>{item}</option>)}</select></label>
          <label>Subgrupo<select value={draft.subgroup ?? ''} onChange={event => setDraft({ ...draft, subgroup: event.target.value || undefined, crop: undefined })}><option value="">Todos los subgrupos</option>{unique(crops.filter(crop => !draft.group || crop.group === draft.group).map(crop => crop.subgroup)).map(item => <option key={item}>{item}</option>)}</select></label>
          <label>Cultivo<select value={draft.crop ?? ''} onChange={event => change('crop', event.target.value ? Number(event.target.value) : undefined)}><option value="">Todos los cultivos</option>{filteredCrops.map(crop => <option key={crop.id} value={crop.id}>{crop.name}</option>)}</select></label>
          <label>Clasificación<select value={draft.classification ?? ''} onChange={event => setDraft({ ...draft, classification: event.target.value || undefined, crop: undefined })}><option value="">Todas</option>{unique(crops.map(crop => crop.general_classification)).map(item => <option key={item}>{item}</option>)}</select></label>
          <label>Tipo de cultivo<select value={draft.cycle ?? ''} onChange={event => setDraft({ ...draft, cycle: event.target.value || undefined, crop: undefined })}><option value="">Todos</option>{unique(crops.map(crop => crop.cycle)).map(item => <option key={item}>{item}</option>)}</select></label>
        </>}
        {filterTab === 'Temporalidad' && <>
          <label>Año inicial<select value={draft.yearFrom} onChange={event => change('yearFrom', Number(event.target.value))}>{years.filter(year => year <= draft.year).map(year => <option key={year}>{year}</option>)}</select></label>
          <label>Año final<select value={draft.year} onChange={event => change('year', Number(event.target.value))}>{years.filter(year => year >= draft.yearFrom).map(year => <option key={year}>{year}</option>)}</select></label>
          <label>Lectura temporal<select value={draft.periodMode === 'AGRICULTURAL_YEAR' ? 'AGRICULTURAL_YEAR' : draft.periodType ?? 'ANNUAL'} onChange={event => setDraft({ ...draft, periodMode: event.target.value === 'AGRICULTURAL_YEAR' ? 'AGRICULTURAL_YEAR' : 'SOURCE', periodType: event.target.value === 'AGRICULTURAL_YEAR' ? undefined : event.target.value as Query['periodType'] })}><option value="AGRICULTURAL_YEAR">Año agrícola</option><option value="ANNUAL">Anual de la fuente</option><option value="SEMESTER_A">Semestre A</option><option value="SEMESTER_B">Semestre B</option></select></label>
          <label className="aq-check"><input type="checkbox" checked={draft.compare} onChange={event => change('compare', event.target.checked)} />Comparar con otro periodo</label>
          <label>Año de comparación<select disabled={!draft.compare} value={draft.compareYear} onChange={event => change('compareYear', Number(event.target.value))}>{years.map(year => <option key={year}>{year}</option>)}</select></label>
        </>}
        {filterTab === 'Indicadores' && <>
          <label>Indicador principal{metricSelect(draft.indicator, value => setDraft({ ...draft, indicator: value, orderBy: value }), 'Indicador principal del panel')}</label>
          <label>Indicador secundario<select value={draft.secondary} onChange={event => change('secondary', event.target.value as Query['secondary'])}><option value="">Ninguno</option><MetricOptions /></select></label>
          <label>Agrupar resultados por<select value={draft.dimension} onChange={event => change('dimension', event.target.value as Query['dimension'])}>{Object.entries(dimensions).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label>Ordenar por{metricSelect(draft.orderBy, value => change('orderBy', value), 'Ordenar por en el panel')}</label>
          <label>Dirección<select value={draft.direction} onChange={event => change('direction', event.target.value as Query['direction'])}><option value="desc">Descendente</option><option value="asc">Ascendente</option></select></label>
          <label>Número de resultados<select value={draft.limit} onChange={event => change('limit', Number(event.target.value))}>{[10, 20, 50, 100].map(value => <option key={value} value={value}>Top {value}</option>)}</select></label>
          <label className="aq-check"><input type="checkbox" checked={draft.showVariation} onChange={event => change('showVariation', event.target.checked)} />Mostrar variación</label>
        </>}
        {filterTab !== 'Territorio' && <p className="aq-hint">Los filtros se sincronizan con los paneles superiores. Pulsa «Ejecutar consulta» para actualizar los resultados.</p>}
        </div>
      </aside>
      <section className="aq-card aq-variables" id="aq-variables"><h2><Sprout />2. Selección de variables</h2>
        <label>Grupo de cultivo<select value={draft.group ?? ''} onChange={event => setDraft({ ...draft, group: event.target.value || undefined, subgroup: undefined, crop: undefined })}><option value="">Todos los grupos</option>{unique(crops.map(crop => crop.group)).map(item => <option key={item}>{item}</option>)}</select></label>
        <label>Subgrupo<select value={draft.subgroup ?? ''} onChange={event => setDraft({ ...draft, subgroup: event.target.value || undefined, crop: undefined })}><option value="">Todos los subgrupos</option>{unique(crops.filter(crop => !draft.group || crop.group === draft.group).map(crop => crop.subgroup)).map(item => <option key={item}>{item}</option>)}</select></label>
        <label>Cultivo<select value={draft.crop ?? ''} onChange={event => change('crop', event.target.value ? Number(event.target.value) : undefined)}><option value="">Todos los cultivos</option>{filteredCrops.map(crop => <option key={crop.id} value={crop.id}>{crop.name}</option>)}</select></label>
        <label>Clasificación<select value={draft.classification ?? ''} onChange={event => setDraft({ ...draft, classification: event.target.value || undefined, crop: undefined })}><option value="">Todas</option>{unique(crops.map(crop => crop.general_classification)).map(item => <option key={item}>{item}</option>)}</select></label>
        <label>Tipo de cultivo</label><div className="aq-tabs">{['', ...unique(crops.map(crop => crop.cycle))].map(cycle => <button key={cycle} className={(draft.cycle ?? '') === cycle ? 'active' : ''} onClick={() => setDraft({ ...draft, cycle: cycle || undefined, crop: undefined })}>{cycle || 'Todos'}</button>)}</div>
      </section>
      <section className="aq-card aq-time" id="aq-time"><h2><CalendarDays />3. Temporalidad</h2><label>Rango de años</label><div className="aq-range"><input aria-label="Año inicial" type="range" min="2019" max="2025" value={draft.yearFrom} onChange={event => change('yearFrom', Math.min(Number(event.target.value), draft.year))} /><input aria-label="Año final" type="range" min="2019" max="2025" value={draft.year} onChange={event => change('year', Math.max(Number(event.target.value), draft.yearFrom))} /></div><div className="aq-range-labels"><span>{draft.yearFrom}</span><span>{draft.year}</span></div>
        <label>Lectura temporal<select value={draft.periodMode === 'AGRICULTURAL_YEAR' ? 'AGRICULTURAL_YEAR' : draft.periodType ?? 'ANNUAL'} onChange={event => setDraft({ ...draft, periodMode: event.target.value === 'AGRICULTURAL_YEAR' ? 'AGRICULTURAL_YEAR' : 'SOURCE', periodType: event.target.value === 'AGRICULTURAL_YEAR' ? undefined : event.target.value as Query['periodType'] })}><option value="AGRICULTURAL_YEAR">Año agrícola</option><option value="ANNUAL">Anual de la fuente</option><option value="SEMESTER_A">Semestre A</option><option value="SEMESTER_B">Semestre B</option></select></label>
        <label className="aq-check"><input type="checkbox" checked={draft.compare} onChange={event => change('compare', event.target.checked)} />Comparar con otro periodo</label><label>Periodo de comparación</label><div className="aq-comparison"><select aria-label="Año de comparación" disabled={!draft.compare} value={draft.compareYear} onChange={event => change('compareYear', Number(event.target.value))}>{years.map(year => <option key={year}>{year}</option>)}</select><span>vs</span><select aria-label="Año comparado" disabled={!draft.compare} value={draft.year} onChange={event => setDraft({ ...draft, year: Number(event.target.value), yearFrom: Math.min(draft.yearFrom, Number(event.target.value)) })}>{years.map(year => <option key={year}>{year}</option>)}</select></div>
        <p className="aq-hint">La tabla y el mapa muestran {draft.year}; la gráfica, el rango seleccionado.</p>
      </section>
      <section className="aq-card aq-indicators" id="aq-indicators"><h2><BarChart3 />4. Indicadores</h2><label>Indicador principal{metricSelect(draft.indicator, value => setDraft({ ...draft, indicator: value, orderBy: value }), 'Indicador principal')}</label><label>Indicador secundario (opcional)<select value={draft.secondary} onChange={event => change('secondary', event.target.value as Query['secondary'])}><option value="">Ninguno</option><MetricOptions /></select></label><label>Agrupar resultados por</label><div className="aq-tabs">{Object.entries(dimensions).map(([key, label]) => <button key={key} className={draft.dimension === key ? 'active' : ''} onClick={() => change('dimension', key as Query['dimension'])}>{label}</button>)}</div>
        <label>Ordenar por</label><div className="aq-two">{metricSelect(draft.orderBy, value => change('orderBy', value), 'Ordenar por')}<select aria-label="Dirección de orden" value={draft.direction} onChange={event => change('direction', event.target.value as Query['direction'])}><option value="desc">Descendente</option><option value="asc">Ascendente</option></select></div><label>Número de resultados</label><div className="aq-two"><select aria-label="Número de resultados" value={draft.limit} onChange={event => change('limit', Number(event.target.value))}>{[10, 20, 50, 100].map(value => <option key={value} value={value}>Top {value}</option>)}</select><label className="aq-check aq-toggle"><input type="checkbox" checked={draft.showVariation} onChange={event => change('showVariation', event.target.checked)} />Mostrar variación</label></div><button className="aq-run" disabled={busy} onClick={() => void execute({ ...draft, compareYear: draft.compare ? draft.compareYear : Math.max(2019, draft.year - 1) })}><Search size={13} />{busy ? 'Consultando…' : 'Ejecutar consulta'}</button>
      </section>
      <section className="aq-card aq-results" aria-busy={busy}><header className="aq-results__header"><h2><Database />Resultados de la consulta</h2><div className="aq-actions"><button onClick={save} disabled={!result || busy}><Save />Guardar consulta</button><label className="aq-load"><FolderOpen /><select aria-label="Cargar consulta guardada" value="" onChange={event => { const entry = saved[Number(event.target.value)]; if (entry) { setDraft(entry.query); void execute(entry.query); setNotice('Consulta recuperada.'); } }}><option value="">Cargar consulta</option>{saved.map((entry, index) => <option value={index} key={index}>{entry.name}</option>)}</select></label><button onClick={exportCsv} disabled={!result || busy}><Download />Exportar</button></div></header>
        {error && <p className="aq-error" role="alert">{error}</p>}{notice && <p className="aq-notice" role="status">{notice}</p>}{dirty && !busy && <p className="aq-hint">Hay filtros sin aplicar. Pulsa «Ejecutar consulta».</p>}
        <div className="aq-results-grid"><div className="aq-table-section"><nav className="aq-tabs" aria-label="Vista de resultados">{['Tabla', 'Gráfica', 'Mapa', 'Resumen'].map(name => <button key={name} className={view === name ? 'active' : ''} onClick={() => setView(name)}>{name}</button>)}</nav>
          <p className="aq-hint">{applied.dimension === 'year' ? `${applied.yearFrom}–${applied.year}` : `Corte ${applied.year}`} · {place} · {crops.find(crop => crop.id === applied.crop)?.name ?? 'Todos los cultivos'}</p>
          {view === 'Tabla' && <><div className="aq-table-scroll"><table><thead><tr><th>#</th><th>{dimensions[applied.dimension]}</th>{applied.dimension === 'municipality' && <th>Departamento</th>}<th>Área sembrada<br />(ha)</th><th>Área cosechada<br />(ha)</th><th>Producción (t)</th><th>Rendimiento<br />(t/ha)</th>{applied.showVariation && <th>Variación<small>{applied.compareYear}–{applied.year}</small></th>}</tr></thead><tbody>{rows.map((row, index) => <tr key={row.id}><td>{(page - 1) * pageSize + index + 1}</td><td>{row.name}</td>{applied.dimension === 'municipality' && <td>{row.department}</td>}<td>{number(row.planted_area_ha)}</td><td>{number(row.harvested_area_ha)}</td><td>{number(row.production_t)}</td><td>{number(row.yield_t_ha)}</td>{applied.showVariation && <td className={row.variation == null ? '' : row.variation >= 0 ? 'aq-positive' : 'aq-negative'}>{row.variation == null ? '—' : `${row.variation >= 0 ? '↑' : '↓'} ${number(row.variation, 1)} %`}</td>}</tr>)}</tbody></table>{!rows.length && <p className="aq-empty">{busy ? 'Cargando resultados…' : 'No hay datos para esta selección.'}</p>}</div><footer className="aq-pagination"><span>{result?.rows.length ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, result.rows.length)}` : '0'} de {result?.rows.length ?? 0} resultados</span><div><button aria-label="Página anterior" disabled={page <= 1} onClick={() => setPage(page - 1)}><ChevronLeft /></button><span className="aq-page">{page}</span><span> / {pages}</span><button aria-label="Página siguiente" disabled={page >= pages} onClick={() => setPage(page + 1)}><ChevronRight /></button></div><label>Por página<select value={pageSize} onChange={event => { setPageSize(Number(event.target.value)); setPage(1); }}>{[10, 20, 50].map(value => <option key={value}>{value}</option>)}</select></label></footer></>}
          {view === 'Gráfica' && <section className="aq-expanded-chart"><header><h3>Evolución de {metrics[applied.indicator].split(' (')[0].toLowerCase()}</h3><select aria-label="Tipo de gráfica" value={chartType} onChange={event => setChartType(event.target.value)}><option value="line">Línea</option><option value="bar">Barras</option></select></header><EChart ariaLabel="Comparación histórica; eje X: Año; ejes Y: indicadores seleccionados" option={graph} items={result?.series.map(point => ({ label: String(point.year), value: number(point[applied.indicator]) })) ?? []} /></section>}
          {view === 'Mapa' && <div className="aq-expanded-map"><TerritorialMap filters={{ ...applied, yearFrom: applied.year }} onSelect={(level, code) => { const next = { ...applied, [level]: code, ...(level === 'department' ? { municipality: undefined } : {}) }; setDraft(next); void execute(next); }} /></div>}
          {view === 'Resumen' && <div className="aq-summary">{Object.entries(metrics).map(([key, label]) => <div key={key}><span>{label}</span><strong>{number(result?.summary?.[key as Indicator])}</strong></div>)}<p>{result?.total ?? 0} grupos con datos; se muestran los primeros {result?.rows.length ?? 0} según el orden elegido.</p></div>}
        </div></div>
      </section>
      <section className="aq-card aq-top"><h2>Top municipios por rendimiento <InfoTooltip label="Rendimiento municipal" content="Producción dividida por área cosechada. Ranking del último año seleccionado; no es un promedio de rendimientos." /></h2><p className="aq-hint">Rendimiento (t/ha) · {applied.year}</p>{result?.top_yield.map((row, index) => <div className="aq-yield-row" key={row.id}><span>{index + 1}</span><span title={`${row.name} (${row.department})`}>{row.name}</span><i><b style={{ width: `${Math.max(0, (row.yield_t_ha ?? 0) / (result.top_yield[0]?.yield_t_ha || 1) * 100)}%` }} /></i><strong>{number(row.yield_t_ha)}</strong></div>)}</section>
      <section className="aq-card aq-variation"><h2>Variación {applied.compareYear} - {applied.year}<InfoTooltip label="Lectura de la variación" content={`Compara ${metrics[applied.indicator]} entre años para todos los grupos, no solo el top visible. Sin base comparable o base cero se muestra —.`} /></h2><div><span className="aq-arrow"><ArrowUp /></span><p><strong>{result?.increases ?? 0}</strong>{dimensions[applied.dimension]}s<br />con aumento</p><span className="aq-arrow aq-arrow--down"><ArrowDown /></span><p><strong>{result?.decreases ?? 0}</strong>{dimensions[applied.dimension]}s<br />con disminución</p></div></section>
      <section className="aq-card aq-composition"><h2>Composición por tipo de cultivo</h2><EChart ariaLabel={`Participación por tipo de cultivo en ${metrics[compositionMetric]}`} option={composition} items={result?.composition.map(row => ({ label: row.name, value: number(row[compositionMetric]) })) ?? []} /><p className="aq-hint">{metrics[compositionMetric]} · {applied.year}</p></section>
    </div>
    <footer className="aq-methodology">Fuente: datos obtenidos de EVA · UPRA. {response?.methodology.join(' ')} {response?.warnings.map(warning => warning.message).join(' ')}</footer>
  </section>;
}
