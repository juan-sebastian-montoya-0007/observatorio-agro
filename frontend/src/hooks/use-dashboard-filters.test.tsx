import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardFilters } from "@/components/dashboard/dashboard-filters";

import {
  clearDepartment,
  readFilters,
  updateFilter,
  useDashboardFilters,
  writeFilters,
} from "./use-dashboard-filters";

const navigation = vi.hoisted(() => ({
  pathname: "/",
  replace: vi.fn(),
  search: "department=05&municipality=05001&year=2024",
}));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
  useRouter: () => ({ replace: navigation.replace }),
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

describe("dashboard filter URL state", () => {
  beforeEach(() => {
    navigation.replace.mockReset();
    navigation.search = "department=05&municipality=05001&year=2024";
  });

  it("reads textual territory codes and fills only absent defaults", () => {
    expect(
      readFilters("?department=05&municipality=05001&year=2024"),
    ).toEqual({
      department: "05",
      municipality: "05001",
      year: 2024,
      periodMode: "AGRICULTURAL_YEAR",
      indicator: "production_t",
    });
  });

  it("rejects an orphan municipality and invalid URL values", () => {
    expect(readFilters("?municipality=05001&year=abc&period_mode=OTHER")).toEqual({
      year: 2025,
      periodMode: "AGRICULTURAL_YEAR",
      indicator: "production_t",
    });
  });

  it("clears municipality when department changes or is removed", () => {
    const filters = readFilters("?department=05&municipality=05001&year=2024");

    expect(clearDepartment(filters).municipality).toBeUndefined();
    expect(updateFilter(filters, "department", "08").municipality).toBeUndefined();
  });

  it("replaces the current URL when a filter changes and can reset it", () => {
    const { result } = renderHook(() => useDashboardFilters());

    act(() => result.current.setFilter("department", "08"));
    const changedUrl = new URL(navigation.replace.mock.calls[0][0], "http://local");
    expect(changedUrl.searchParams.get("department")).toBe("08");
    expect(changedUrl.searchParams.has("municipality")).toBe(false);
    expect(changedUrl.searchParams.get("year")).toBe("2024");

    act(() => result.current.resetFilters());
    expect(navigation.replace).toHaveBeenLastCalledWith("/", { scroll: false });
  });

  it("adds a valid source period when switching modes and removes it on return", () => {
    const { result, rerender } = renderHook(() => useDashboardFilters());

    act(() => result.current.setFilter("periodMode", "SOURCE"));
    const sourceUrl = new URL(navigation.replace.mock.calls[0][0], "http://local");
    expect(sourceUrl.searchParams.get("period_type")).toBe("ANNUAL");
    navigation.search = sourceUrl.search;
    rerender();
    expect(result.current.filters.periodType).toBe("ANNUAL");

    act(() => result.current.setFilter("periodMode", "AGRICULTURAL_YEAR"));
    const annualUrl = new URL(navigation.replace.mock.calls[1][0], "http://local");
    expect(annualUrl.searchParams.has("period_type")).toBe(false);
    expect(readFilters(annualUrl.search).periodType).toBeUndefined();
  });

  it.each(["ANNUAL", "SEMESTER_A", "SEMESTER_B"] as const)(
    "preserves %s through URL serialization and reload",
    (periodType) => {
      const filters = readFilters(`period_mode=SOURCE&period_type=${periodType}&year=2024`);
      expect(filters.periodType).toBe(periodType);
      expect(readFilters(writeFilters(filters))).toEqual(filters);
    },
  );

  it.each(["", "&period_type=OTHER"])(
    "normalizes missing or invalid source periods to annual (%s)",
    (query) => {
      const filters = readFilters(`period_mode=SOURCE${query}`);
      expect(filters.periodType).toBe("ANNUAL");
      expect(writeFilters(filters).get("period_type")).toBe("ANNUAL");
    },
  );

  it("discards a source period in agricultural year mode", () => {
    const filters = readFilters("period_mode=AGRICULTURAL_YEAR&period_type=SEMESTER_B");
    expect(filters.periodType).toBeUndefined();
    expect(writeFilters({ ...filters, periodType: "SEMESTER_B" }).has("period_type")).toBe(false);
  });

  it("offers a source selector and persists its selected semester", () => {
    function FilterPanel() {
      const { filters, setFilter, resetFilters } = useDashboardFilters();
      return (
        <DashboardFilters
          crops={[]}
          departments={[]}
          municipalities={[]}
          filters={filters}
          onChange={setFilter}
          onReset={resetFilters}
        />
      );
    }
    const { rerender } = render(<FilterPanel />);
    expect(screen.queryByRole("combobox", { name: "Periodo de la fuente" })).toBeNull();

    navigation.search = "period_mode=SOURCE&period_type=SEMESTER_A";
    rerender(<FilterPanel />);
    const selector = screen.getByRole("combobox", { name: "Periodo de la fuente" });
    expect(selector).toHaveValue("SEMESTER_A");
    expect(selector.querySelectorAll("option")).toHaveLength(3);
    fireEvent.change(selector, { target: { value: "SEMESTER_B" } });
    const url = new URL(navigation.replace.mock.calls[0][0], "http://local");
    expect(url.searchParams.get("period_type")).toBe("SEMESTER_B");
    navigation.search = url.search;
    rerender(<FilterPanel />);
    expect(screen.getByRole("combobox", { name: "Periodo de la fuente" })).toHaveValue("SEMESTER_B");
  });
});
