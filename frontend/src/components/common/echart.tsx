"use client";

import { useEffect, useRef } from "react";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import type { EChartsCoreOption } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  AriaComponent,
  BarChart,
  CanvasRenderer,
  GridComponent,
  LegendComponent,
  LineChart,
  PieChart,
  TooltipComponent,
]);

type AccessibleItem = { label: string; value: string };

type EChartProps = {
  ariaLabel: string;
  items: AccessibleItem[];
  option: EChartsCoreOption;
};

export function EChart({ ariaLabel, items, option }: EChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || process.env.NODE_ENV === "test") return;
    const chart = echarts.init(containerRef.current, undefined, { renderer: "canvas" });
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);

  return (
    <>
      <div className="chart-canvas" ref={containerRef} role="img" aria-label={ariaLabel} />
      <details className="chart-data">
        <summary>Ver datos en texto</summary>
        <ul>
          {items.map((item) => (
            <li key={`${item.label}-${item.value}`}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}
