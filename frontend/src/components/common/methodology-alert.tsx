import { TriangleAlert } from "lucide-react";

import type { AnalyticalWarning } from "@/types/api";

export function MethodologyAlert({ warnings }: { warnings: AnalyticalWarning[] }) {
  if (warnings.length === 0) return null;

  return (
    <aside className="methodology-alert" aria-label="Advertencias metodológicas">
      <TriangleAlert size={21} aria-hidden="true" />
      <div>
        <h3>Cobertura metodológica parcial</h3>
        {warnings.map((warning) => (
          <p key={warning.code}>{warning.message}</p>
        ))}
      </div>
    </aside>
  );
}
