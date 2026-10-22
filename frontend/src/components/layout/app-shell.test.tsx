import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("renders the institutional navigation and marks future cuts as unavailable", () => {
    render(
      <AppShell>
        <p>Contenido real</p>
      </AppShell>,
    );

    expect(screen.getByRole("navigation", { name: "Navegación principal" })).toBeVisible();
    expect(screen.getByRole("link", { name: /Resumen General/i })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByText("Geovisor")).toBeVisible();
    expect(screen.getAllByText("Próximamente")).toHaveLength(5);
    expect(screen.getByRole("heading", { name: "EVA Explorer" })).toBeVisible();
    expect(screen.getByText("Contenido real")).toBeVisible();
  });
});
