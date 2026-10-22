import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "./page";


describe("HomePage", () => {
  it("identifies EVA Explorer without inventing agricultural figures", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: "EVA Explorer" })).toBeVisible();
    expect(screen.getByText("Cargando datos agrícolas…")).toBeVisible();
  });
});
