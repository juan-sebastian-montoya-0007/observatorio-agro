import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearDepartment,
  readFilters,
  updateFilter,
  useDashboardFilters,
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
});
