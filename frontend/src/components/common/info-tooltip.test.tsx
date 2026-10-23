import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InfoTooltip } from "./info-tooltip";

describe("InfoTooltip", () => {
  it("keeps focused help open when the pointer leaves and links it to the trigger", () => {
    render(
      <InfoTooltip
        label="Información sobre rendimiento"
        content="Se calcula como producción dividida por área cosechada."
      />,
    );

    const trigger = screen.getByRole("button", { name: "Información sobre rendimiento" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    fireEvent.focus(trigger);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent(
      "Se calcula como producción dividida por área cosechada.",
    );
    expect(trigger).toHaveAttribute("aria-describedby", tooltip.id);

    const wrapper = trigger.parentElement!;
    fireEvent.mouseEnter(wrapper);
    fireEvent.mouseLeave(wrapper);
    expect(screen.getByRole("tooltip")).toBeVisible();

    fireEvent.blur(trigger);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("reveals contextual help on hover", () => {
    render(
      <InfoTooltip
        label="Información sobre producción"
        content="Suma de toneladas reportadas para la selección."
      />,
    );

    const trigger = screen.getByRole("button", { name: "Información sobre producción" });
    const wrapper = trigger.parentElement!;
    fireEvent.mouseEnter(wrapper);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Suma de toneladas");

    fireEvent.mouseLeave(wrapper);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("closes with Escape without removing keyboard focus", () => {
    render(
      <InfoTooltip
        label="Información sobre producción"
        content="Suma de toneladas reportadas para la selección."
      />,
    );

    const trigger = screen.getByRole("button", { name: "Información sobre producción" });
    trigger.focus();
    fireEvent.focus(trigger);
    expect(screen.getByRole("tooltip")).toBeVisible();

    fireEvent.keyDown(trigger, { key: "Escape" });

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("closes hover-only help when Escape is pressed anywhere in the document", () => {
    render(
      <InfoTooltip
        label="Información sobre producción"
        content="Suma de toneladas reportadas para la selección."
      />,
    );

    const trigger = screen.getByRole("button", { name: "Información sobre producción" });
    fireEvent.mouseEnter(trigger.parentElement!);
    expect(screen.getByRole("tooltip")).toBeVisible();
    expect(trigger).not.toHaveFocus();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});
