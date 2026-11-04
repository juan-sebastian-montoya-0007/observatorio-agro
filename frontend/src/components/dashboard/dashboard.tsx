"use client";

import { CalendarDays, Database, MapPin } from "lucide-react";
import { useEffect, useState } from "react";

import { useDashboardFilters } from "@/hooks/use-dashboard-filters";
import { getRankings, getSeries, getSummary } from "@/services/agriculture";
import { getCatalogs, getDepartments, getMunicipalities } from "@/services/catalog";
import type {
  AnalyticalEnvelope,
  Crop,
  Department,
  Municipality,
  RankingItem,
  SeriesPoint,
  Summary,
} from "@/types/api";

import { DashboardLoading, EmptyState, ErrorState } from "../common/async-state";
import { MethodologyAlert } from "../common/methodology-alert";
import { CropDistribution } from "./crop-distribution";
import { CropRanking } from "./crop-ranking";
import { DashboardFilters } from "./dashboard-filters";
import { HistoricalSeries } from "./historical-series";
import { KpiGrid } from "./kpi-grid";
import { TerritorialRanking } from "./territorial-ranking";
import { TerritorialMap } from "./territorial-map";

type DashboardData = {
  crops: AnalyticalEnvelope<RankingItem[]>;
  series: AnalyticalEnvelope<SeriesPoint[]>;
  summary: AnalyticalEnvelope<Summary | null>;
  territories: AnalyticalEnvelope<RankingItem[]>;
  municipalities: AnalyticalEnvelope<RankingItem[]>;
};

type DashboardResult = {
  data: DashboardData;
  requestKey: string;
};

export function Dashboard() {
  const { filters, resetFilters, setFilter } = useDashboardFilters();
  const [crops, setCrops] = useState<Crop[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [result, setResult] = useState<DashboardResult | null>(null);
  const [failedRequestKey, setFailedRequestKey] = useState<string | null>(null);
  const [catalogError, setCatalogError] = useState(false);
  const [reload, setReload] = useState(0);

  const requestKey = [
    filters.department,
    filters.municipality,
    filters.crop,
    filters.cropVariant,
    filters.group,
    filters.subgroup,
    filters.cycle,
    filters.physicalState,
    filters.year,
    filters.periodMode,
    filters.periodType,
    filters.indicator,
    reload,
  ].join("|");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([getCatalogs(controller.signal), getDepartments(controller.signal)])
      .then(([catalogs, departmentResponse]) => {
        setCrops(catalogs.crops.data);
        setDepartments(departmentResponse.data);
        setCatalogError(false);
      })
      .catch((cause: unknown) => {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) {
          setCatalogError(true);
        }
      });
    return () => controller.abort();
  }, [reload]);

  useEffect(() => {
    if (!filters.department) return;
    const controller = new AbortController();
    getMunicipalities(filters.department, controller.signal)
      .then((response) => setMunicipalities(response.data))
      .catch((cause: unknown) => {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) {
          setCatalogError(true);
        }
      });
    return () => controller.abort();
  }, [filters.department, reload]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getSummary(filters, controller.signal),
      getSeries(filters, controller.signal),
      getRankings(filters, "crop", 10, controller.signal),
      getRankings(filters, "department", 7, controller.signal),
      getRankings(filters, "municipality", 7, controller.signal),
    ])
      .then(([summary, series, cropResponse, territories, municipalityResponse]) => {
        setResult({
          requestKey,
          data: { summary, series, crops: cropResponse, territories, municipalities: municipalityResponse },
        });
        setFailedRequestKey(null);
      })
      .catch((cause: unknown) => {
        if (!(cause instanceof DOMException && cause.name === "AbortError")) {
          setFailedRequestKey(requestKey);
        }
      });
    return () => controller.abort();
  }, [filters, requestKey]);

  useEffect(() => {
    const search = (event: Event) => {
      const query = (event as CustomEvent<string>).detail.trim().toLocaleLowerCase("es").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      const matches = (name: string) => name.toLocaleLowerCase("es").normalize("NFD").replace(/[\u0300-\u036f]/g, "").includes(query);
      if (!query) return;
      const crop = crops.find((item) => matches(item.name));
      const department = departments.find((item) => matches(item.name));
      const municipality = municipalities.find((item) => matches(item.name));
      if (crop) setFilter("crop", crop.id);
      else if (department) setFilter("department", department.code);
      else if (municipality) setFilter("municipality", municipality.code);
      window.dispatchEvent(new CustomEvent("agro:search-result", { detail: crop?.name ?? department?.name ?? municipality?.name ?? "Sin coincidencias. Prueba un cultivo o departamento." }));
    };
    const exportSummary = () => {
      if (!result?.data.summary.data || result.requestKey !== requestKey) return;
      const values = result.data.summary.data;
      const csv = ["Indicador;Valor;Unidad;Año;Departamento;Cultivo;Fuente", ...[
        ["Área sembrada", values.planted_area_ha, "ha"],
        ["Área cosechada", values.harvested_area_ha, "ha"],
        ["Producción", values.production_t, "t"],
        ["Rendimiento", values.yield_t_ha ?? "", "t/ha"],
      ].map((row) => [...row, filters.year, filters.department ?? "Colombia", filters.crop ?? "Todos", "EVA - UPRA"].join(";"))].join("\r\n");
      const url = URL.createObjectURL(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `observatorio-agro-resumen-${filters.year}.csv`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
    window.addEventListener("agro:search", search);
    window.addEventListener("agro:export", exportSummary);
    return () => {
      window.removeEventListener("agro:search", search);
      window.removeEventListener("agro:export", exportSummary);
    };
  }, [crops, departments, municipalities, filters, result, requestKey, setFilter]);

  const retry = () => setReload((value) => value + 1);
  const loading = result?.requestKey !== requestKey && failedRequestKey !== requestKey;
  const error = catalogError || failedRequestKey === requestKey;

  if (loading) return <DashboardLoading />;
  if (error || result === null) return <ErrorState onRetry={retry} />;

  const { data } = result;
  const { summary } = data;
  const isEmpty = summary.data === null || summary.coverage.status === "EMPTY";

  return (
    <section className="dashboard">
      <header className="dashboard__intro">
        <div>
          <span className="dashboard__kicker">Panorama nacional</span>
          <h2>Resumen General</h2>
          <p>El campo colombiano, en datos. Explora su producción y sus territorios.</p>
        </div>
        <div className="dashboard__context" id="fuente-datos">
          <span>
            <MapPin size={15} aria-hidden="true" />
            {departments.find((item) => item.code === filters.department)?.name ?? "Colombia"}
          </span>
          <span>
            <CalendarDays size={15} aria-hidden="true" />
            {filters.year} · {filters.periodMode === "AGRICULTURAL_YEAR" ? "Año agrícola" : "Fuente"}
          </span>
          <span>
            <Database size={15} aria-hidden="true" />
            {crops.find((item) => item.id === filters.crop)?.name ?? "Todos los cultivos"}
          </span>
        </div>
        <div className="dashboard__source"><Database size={15} aria-hidden="true" /><div><strong>Datos oficiales</strong><small>Fuente: EVA · UPRA</small></div></div>
      </header>

      <DashboardFilters
        crops={crops}
        departments={departments}
        filters={filters}
        municipalities={filters.department ? municipalities : []}
        onChange={setFilter}
        onReset={resetFilters}
      />

      {isEmpty ? (
        <EmptyState onReset={resetFilters} />
      ) : (
        <>
          <KpiGrid summary={summary.data!} points={data.series.data} year={filters.year} />
          <section className="dashboard-grid" aria-label="Visualizaciones agrícolas">
            <TerritorialMap filters={filters} onSelect={(level, code) => setFilter(level, code)} />
            <HistoricalSeries indicator={filters.indicator} points={data.series.data} onIndicatorChange={(indicator) => setFilter("indicator", indicator)} />
            <CropRanking indicator={filters.indicator} items={data.crops.data} onSelect={(id) => setFilter("crop", Number(id))} />
            <TerritorialRanking
              indicator={filters.indicator}
              items={data.territories.data}
              level="department"
              onSelect={(code) => setFilter("department", code)}
            />
            <TerritorialRanking
              indicator={filters.indicator}
              items={data.municipalities.data}
              level="municipality"
            />
            <CropDistribution
              indicator={filters.indicator}
              items={data.crops.data.slice(0, 5)}
            />
          </section>
          <MethodologyAlert warnings={summary.warnings} />
          <footer className="dashboard__methodology">
            <strong>Cómo leer estas cifras</strong>
            <p>{summary.methodology.join(" ")}</p>
          </footer>
        </>
      )}
    </section>
  );
}
