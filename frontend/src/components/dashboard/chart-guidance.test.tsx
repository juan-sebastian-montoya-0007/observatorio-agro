import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RankingItem, SeriesPoint } from "@/types/api";

import { buildCropRankingOption, CropRanking } from "./crop-ranking";
import { buildHistoricalSeriesOption, HistoricalSeries } from "./historical-series";

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

describe("chart guidance", () => {
  it("names both historical-series axes with their meaning and unit", () => {
    const option = buildHistoricalSeriesOption("production_t", [point]) as {
      aria: { description?: string };
      xAxis: { name?: string };
      yAxis: { name?: string };
    };

    expect(option.aria.description).toBe(
      "Serie histórica de Producción; eje horizontal: Año; eje vertical: Producción (t)",
    );
    expect(option.xAxis.name).toBe("Año");
    expect(option.yAxis.name).toBe("Producción (t)");

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

  it("names both crop-ranking axes and exposes formatted units", () => {
    const option = buildCropRankingOption("production_t", ranking) as {
      aria: { description?: string };
      xAxis: { name?: string; axisLabel: { formatter: (value: number) => string } };
      yAxis: { name?: string };
    };

    expect(option.aria.description).toBe(
      "Ranking de cultivos; eje horizontal: Producción (t); eje vertical: Cultivo",
    );
    expect(option.xAxis.name).toBe("Producción (t)");
    expect(option.xAxis.axisLabel.formatter(10_000_000)).toMatch(/10.*M/i);
    expect(option.yAxis.name).toBe("Cultivo");

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
});
