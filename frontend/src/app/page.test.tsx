import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/dashboard/dashboard", () => ({
  Dashboard: () => (
    <section role="status" aria-label="Cargando panel agrícola">
      Cargando datos agrícolas…
    </section>
  ),
}));

import HomePage from "./page";


describe("HomePage", () => {
  it("identifies Observatorio Agro while the real API data loads", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: "Observatorio Agro" })).toBeVisible();
    expect(screen.getByRole("status", { name: "Cargando panel agrícola" })).toBeVisible();
  });
});
