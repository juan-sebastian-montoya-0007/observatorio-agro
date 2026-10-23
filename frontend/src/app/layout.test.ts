import { describe, expect, it } from "vitest";

import { metadata } from "./layout";

describe("root layout metadata", () => {
  it("uses Observatorio Agro as the browser title", () => {
    expect(metadata.title).toBe("Observatorio Agro");
  });
});
