import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiContractError } from "./http";
import { getSummary } from "./agriculture";

const envelope = {
  data: {
    planted_area_ha: "10.0000",
    harvested_area_ha: "9.0000",
    production_t: "18.0000",
    yield_t_ha: "2.0000",
    record_count: 1,
  },
  meta: { source_version: "2019-2025", source_version_id: 1 },
  coverage: { status: "AVAILABLE", year_from: 2024, year_to: 2024 },
  warnings: [],
  methodology: [],
};

describe("agriculture service", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("calls only summary and preserves leading zeroes in DIVIPOLA codes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(envelope), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getSummary({
      department: "05",
      municipality: "05001",
      year: 2024,
      periodMode: "AGRICULTURAL_YEAR",
      indicator: "production_t",
    });

    expect(result.data?.production_t).toBe("18.0000");
    expect(fetchMock).toHaveBeenCalledOnce();
    const requested = new URL(fetchMock.mock.calls[0][0]);
    expect(requested.pathname).toBe("/api/v1/agriculture/summary");
    expect(requested.searchParams.get("department")).toBe("05");
    expect(requested.searchParams.get("municipality")).toBe("05001");
  });

  it("rejects a response that is not an analytical envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      getSummary({
        year: 2025,
        periodMode: "AGRICULTURAL_YEAR",
        indicator: "production_t",
      }),
    ).rejects.toBeInstanceOf(ApiContractError);
  });
});
