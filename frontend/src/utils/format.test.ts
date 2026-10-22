import { describe, expect, it } from "vitest";

import { formatArea, formatMetric, formatProduction, formatYield } from "./format";

describe("agricultural metric formatters", () => {
  it("keeps a reported zero distinct from an unavailable value", () => {
    expect(formatMetric(0)).toBe("0");
    expect(formatMetric(null)).toBe("No disponible");
  });

  it("accepts decimal strings and includes the correct units", () => {
    expect(formatArea("1234.5000")).toContain("ha");
    expect(formatProduction("54.0000")).toContain("t");
    expect(formatYield("2.0000")).toContain("t/ha");
  });
});
