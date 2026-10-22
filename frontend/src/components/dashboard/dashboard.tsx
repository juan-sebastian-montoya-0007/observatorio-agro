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

type DashboardData = {
  crops: AnalyticalEnvelope<RankingItem[]>;
  series: AnalyticalEnvelope<SeriesPoint[]>;
  summary: AnalyticalEnvelope<Summary | null>;
  territories: AnalyticalEnvelope<RankingItem[]>;
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
    const territoryLevel = filters.department ? "municipality" : "department";
    Promise.all([
      getSummary(filters, controller.signal),
      getSeries(filters, controller.signal),
      getRankings(filters, "crop", 8, controller.signal),
      getRankings(filters, territoryLevel, 8, controller.signal),
    ])
      .then(([summary, series, cropResponse, territories]) => {
        setResult({
          requestKey,
          data: { summary, series, crops: cropResponse, territories },
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
          <p>Indicadores consolidados de las Evaluaciones Agropecuarias Municipales.</p>
        </div>
        <div className="dashboard__context" id="fuente-datos">
          <span>
            <MapPin size={15} aria-hidden="true" />
            {filters.department ?? "Colombia"}
          </span>
          <span>
            <CalendarDays size={15} aria-hidden="true" />
            {filters.year} · {filters.periodMode === "AGRICULTURAL_YEAR" ? "Año agrícola" : "Fuente"}
          </span>
          <span>
            <Database size={15} aria-hidden="true" />
            {summary.meta.source_version ?? "Sin versión publicada"}
          </span>
        </div>
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
          <KpiGrid summary={summary.data!} />
          <MethodologyAlert warnings={summary.warnings} />
          <section className="dashboard-grid" aria-label="Visualizaciones agrícolas">
            <HistoricalSeries indicator={filters.indicator} points={data.series.data} />
            <CropRanking indicator={filters.indicator} items={data.crops.data} />
            <TerritorialRanking
              indicator={filters.indicator}
              items={data.territories.data}
              level={filters.department ? "municipality" : "department"}
            />
            <CropDistribution
              indicator={filters.indicator}
              items={data.crops.data.slice(0, 5)}
            />
          </section>
          <footer className="dashboard__methodology">
            <strong>Cómo leer estas cifras</strong>
            <p>{summary.methodology.join(" ")}</p>
          </footer>
        </>
      )}
    </section>
  );
}
