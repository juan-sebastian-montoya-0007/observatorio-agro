import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AnalyticalEnvelope, RankingItem, SeriesPoint, Summary } from "@/types/api";

import { Dashboard } from "./dashboard";

const mocks = vi.hoisted(() => ({
  filters: {
    year: 2025,
    periodMode: "AGRICULTURAL_YEAR" as const,
    indicator: "production_t" as const,
  },
  getCatalogs: vi.fn(),
  getDepartments: vi.fn(),
  getMunicipalities: vi.fn(),
  getRankings: vi.fn(),
  getSeries: vi.fn(),
  getSummary: vi.fn(),
  resetFilters: vi.fn(),
  setFilter: vi.fn(),
}));

vi.mock("@/hooks/use-dashboard-filters", () => ({
  useDashboardFilters: () => ({
    filters: mocks.filters,
    resetFilters: mocks.resetFilters,
    setFilter: mocks.setFilter,
  }),
}));

vi.mock("@/services/catalog", () => ({
  getCatalogs: mocks.getCatalogs,
  getDepartments: mocks.getDepartments,
  getMunicipalities: mocks.getMunicipalities,
}));

vi.mock("@/services/agriculture", () => ({
  getRankings: mocks.getRankings,
  getSeries: mocks.getSeries,
  getSummary: mocks.getSummary,
}));

function envelope<T>(data: T): AnalyticalEnvelope<T> {
  return {
    data,
    meta: { source_version: "EVA 2019-2025", source_version_id: 1 },
    coverage: { status: "AVAILABLE", year_from: 2019, year_to: 2025 },
    warnings: [],
    methodology: ["Rendimiento calculado como razón de sumas."],
  };
}

const summary: Summary = {
  planted_area_ha: "30.0000",
  harvested_area_ha: "27.0000",
  production_t: "54.0000",
  yield_t_ha: "2.0000",
  record_count: 2,
};

const series: SeriesPoint[] = [
  { ...summary, year: 2025, period_type: "SEMESTER_A" },
];

const cropRanking: RankingItem[] = [
  { rank: 1, id: 1, name: "PAPA", value: "54.0000", record_count: 2 },
];

const territoryRanking: RankingItem[] = [
  { rank: 1, id: "05", name: "ANTIOQUIA", value: "54.0000", record_count: 2 },
];

function resolveCatalogs() {
  mocks.getCatalogs.mockResolvedValue({
    crops: envelope([{ id: 1, base_code: "10807", name: "PAPA", cycle: "TRANSITORIO", group: "ALIMENTARIOS", subgroup: "TUBÉRCULOS", general_classification: "ALIMENTARIOS", variants: [] }]),
    periods: envelope([]),
    sources: envelope([]),
  });
  mocks.getDepartments.mockResolvedValue(
    envelope([{ code: "05", name: "ANTIOQUIA", is_active: true }]),
  );
}

function resolveData() {
  mocks.getSummary.mockResolvedValue(envelope(summary));
  mocks.getSeries.mockResolvedValue(envelope(series));
  mocks.getRankings
    .mockResolvedValueOnce(envelope(cropRanking))
    .mockResolvedValueOnce(envelope(territoryRanking));
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    resolveCatalogs();
  });

  it("keeps a stable loading state while data is pending", () => {
    mocks.getSummary.mockReturnValue(new Promise(() => undefined));
    mocks.getSeries.mockReturnValue(new Promise(() => undefined));
    mocks.getRankings.mockReturnValue(new Promise(() => undefined));

    render(<Dashboard />);

    expect(screen.getByRole("status", { name: "Cargando panel agrícola" })).toBeVisible();
  });

  it("renders real response values, units and accessible chart equivalents", async () => {
    resolveData();
    render(<Dashboard />);

    expect(await screen.findByRole("heading", { name: "Resumen General" })).toBeVisible();
    expect(screen.getAllByText("Producción").length).toBeGreaterThan(0);
    expect(screen.getAllByText("54 t").length).toBeGreaterThan(0);
    expect(screen.getByText("2 t/ha")).toBeVisible();
    expect(screen.getAllByText("PAPA").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("img", { name: "Distribución de Producción (t) por cultivo" }),
    ).toBeVisible();
    expect(
      screen.getByRole("list", {
        name: "Ranking de departamentos por Producción (t)",
      }),
    ).toHaveTextContent("ANTIOQUIA54 t");
    expect(
      screen.getByRole("button", { name: "Información sobre área sembrada" }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Información sobre rendimiento" }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Información sobre distribución por cultivo" }),
    ).toBeVisible();
    expect(screen.queryByText(/dato de ejemplo/i)).not.toBeInTheDocument();
  });

  it("explains an empty response in the context of active filters", async () => {
    mocks.getSummary.mockResolvedValue({
      ...envelope(null),
      coverage: { status: "EMPTY", year_from: null, year_to: null },
    });
    mocks.getSeries.mockResolvedValue(envelope([]));
    mocks.getRankings.mockResolvedValue(envelope([]));

    render(<Dashboard />);

    expect(await screen.findByText("No hay datos para estos filtros")).toBeVisible();
    expect(screen.getByRole("button", { name: "Restablecer filtros" })).toBeVisible();
  });

  it("offers a retry after a recoverable service error", async () => {
    mocks.getSummary
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue(envelope(summary));
    mocks.getSeries.mockResolvedValue(envelope([]));
    mocks.getRankings.mockResolvedValue(envelope([]));

    render(<Dashboard />);
    fireEvent.click(await screen.findByRole("button", { name: "Reintentar" }));

    await waitFor(() => expect(mocks.getSummary).toHaveBeenCalledTimes(2));
  });

  it("places methodology warnings next to the analytical content", async () => {
    resolveData();
    mocks.getSummary.mockResolvedValue({
      ...envelope(summary),
      warnings: [
        {
          code: "PARTIAL_SEMESTER_COVERAGE",
          message: "Solo está disponible uno de los dos semestres.",
        },
      ],
    });

    render(<Dashboard />);

    expect(await screen.findByText("Cobertura metodológica parcial")).toBeVisible();
    expect(screen.getByText("Solo está disponible uno de los dos semestres.")).toBeVisible();
  });
});
