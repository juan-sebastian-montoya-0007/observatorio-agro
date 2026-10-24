import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RankingItem, SeriesPoint } from "@/types/api";
import type { Indicator } from "@/types/filters";

import { CropDistribution } from "./crop-distribution";
import { buildCropRankingOption, CropRanking } from "./crop-ranking";
import { buildHistoricalSeriesOption, HistoricalSeries } from "./historical-series";
import { TerritorialRanking } from "./territorial-ranking";

const point: SeriesPoint = {
  year: 2025,
  period_type: "ANNUAL",
  planted_area_ha: "12.0000",
  harvested_area_ha: "10.0000",
  production_t: "20.0000",
  yield_t_ha: "2.0000",
  record_count: 1,
};

const ranking: RankingItem[] = [
  { rank: 1, id: 1, name: "PAPA", value: "20.0000", record_count: 1 },
];

const indicatorGuidance = [
  ["planted_area_ha", "Área sembrada (ha)"],
  ["harvested_area_ha", "Área cosechada (ha)"],
  ["production_t", "Producción (t)"],
  ["yield_t_ha", "Rendimiento (t/ha)"],
] as const satisfies ReadonlyArray<readonly [Indicator, string]>;

describe("chart guidance", () => {
  it.each(indicatorGuidance)(
    "names both historical-series axes for %s",
    (indicator, labelWithUnit) => {
      const option = buildHistoricalSeriesOption(indicator, [point]) as {
        aria: { description?: string };
        xAxis: { name?: string };
        yAxis: { name?: string };
      };

      expect(option.aria.description).toContain(
        `eje horizontal: Año; eje vertical: ${labelWithUnit}`,
      );
      expect(option.xAxis.name).toBe("Año");
      expect(option.yAxis.name).toBe(labelWithUnit);
    },
  );

  it.each(indicatorGuidance)(
    "names both crop-ranking axes for %s",
    (indicator, labelWithUnit) => {
      const option = buildCropRankingOption(indicator, ranking) as {
        aria: { description?: string };
        xAxis: { name?: string; axisLabel: { formatter: (value: number) => string } };
        yAxis: { name?: string };
      };

      expect(option.aria.description).toContain(
        `eje horizontal: ${labelWithUnit}; eje vertical: Cultivo`,
      );
      expect(option.xAxis.name).toBe(labelWithUnit);
      expect(option.xAxis.axisLabel.formatter(10_000_000)).toMatch(/10.*M/i);
      expect(option.yAxis.name).toBe("Cultivo");
    },
  );

  it("exposes historical-series axes through the chart name", () => {
    render(<HistoricalSeries indicator="production_t" points={[point]} />);

    expect(
      screen.getByRole("img", {
        name: "Gráfico de Producción; eje horizontal: Año; eje vertical: Producción (t)",
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Información sobre la serie histórica" }),
    ).toBeVisible();
  });

  it("exposes crop-ranking axes through the chart name", () => {
    render(<CropRanking indicator="production_t" items={ranking} />);

    expect(
      screen.getByRole("img", {
        name: "Gráfico de principales cultivos; eje horizontal: Producción (t); eje vertical: Cultivo",
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Información sobre principales cultivos" }),
    ).toBeVisible();
  });

  it("names crop distribution with its indicator and unit and keeps text data", () => {
    render(<CropDistribution indicator="production_t" items={ranking} />);

    expect(
      screen.getByRole("img", { name: "Distribución de Producción (t) por cultivo" }),
    ).toBeVisible();
    fireEvent.click(screen.getByText("Ver datos en texto"));
    expect(screen.getByText("PAPA")).toBeVisible();
    expect(screen.getByText("20 t")).toBeVisible();
  });

  it("names territorial ranking with its level, indicator and unit and keeps text data", () => {
    render(
      <TerritorialRanking indicator="production_t" items={ranking} level="department" />,
    );

    const list = screen.getByRole("list", {
      name: "Ranking de departamentos por Producción (t)",
    });
    expect(within(list).getByText("PAPA")).toBeVisible();
    expect(within(list).getByText("20 t")).toBeVisible();
  });
});
