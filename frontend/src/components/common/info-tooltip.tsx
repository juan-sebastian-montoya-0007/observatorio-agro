"use client";

import { Info } from "lucide-react";
import { useEffect, useId, useState } from "react";

export function InfoTooltip({ label, content }: { label: string; content: string }) {
  const tooltipId = useId();
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const open = (hovered || focused) && !dismissed;

  useEffect(() => {
    if (!open) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDismissed(true);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  return (
    <span
      className="info-tooltip"
      onMouseEnter={() => {
        setHovered(true);
        setDismissed(false);
      }}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        type="button"
        className="info-tooltip__trigger"
        aria-label={label}
        aria-describedby={open ? tooltipId : undefined}
        aria-expanded={open}
        onBlur={() => {
          setFocused(false);
          setDismissed(false);
        }}
        onClick={() => setDismissed(false)}
        onFocus={() => {
          setFocused(true);
          setDismissed(false);
        }}
      >
        <Info size={14} strokeWidth={2} aria-hidden="true" />
      </button>
      {open ? (
        <span className="info-tooltip__content" id={tooltipId} role="tooltip">
          {content}
        </span>
      ) : null}
    </span>
  );
}
