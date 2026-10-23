import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("renders the Observatorio Agro identity and approved navigation", () => {
    render(
      <AppShell>
        <p>Contenido real</p>
      </AppShell>,
    );

    const navigation = screen.getByRole("navigation", { name: "Navegación principal" });

    expect(navigation).toBeVisible();
    expect(within(navigation).getAllByRole("listitem")).toHaveLength(5);
    expect(screen.getByRole("link", { name: /Resumen General/i })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByText("Consultas")).toBeVisible();
    expect(screen.getByText("Comparador")).toBeVisible();
    expect(screen.getByText("Repositorio")).toBeVisible();
    expect(screen.getByText("Acerca de")).toBeVisible();
    expect(screen.getAllByText("Próximamente")).toHaveLength(4);
    expect(screen.getByRole("heading", { name: "Observatorio Agro" })).toBeVisible();
    expect(screen.getByLabelText("Observatorio Agro")).toBeVisible();
    expect(
      screen.getByText(
        "Datos obtenidos de las Evaluaciones Agropecuarias Municipales (EVA), publicadas por la UPRA.",
      ),
    ).toBeVisible();
    expect(screen.getByText("Contenido real")).toBeVisible();
  });
});
