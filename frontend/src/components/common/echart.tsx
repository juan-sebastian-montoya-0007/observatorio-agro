"use client";

import { useEffect, useRef } from "react";
import { BarChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import type { EChartsCoreOption } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useDarkTheme } from "../layout/theme-toggle";

echarts.use([
  AriaComponent,
  BarChart,
  CanvasRenderer,
  GridComponent,
  LegendComponent,
  LineChart,
  PieChart,
  ScatterChart,
  TooltipComponent,
]);

type AccessibleItem = { label: string; value: string };

type EChartProps = {
  ariaLabel: string;
  items: AccessibleItem[];
  option: EChartsCoreOption;
};

export function EChart({ ariaLabel, items, option }: EChartProps) {
  const dark = useDarkTheme();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || process.env.NODE_ENV === "test") return;
    const chart = echarts.init(containerRef.current, dark ? 'dark' : undefined, { renderer: "canvas" });
    const themed: EChartsCoreOption = { ...option, backgroundColor: 'transparent' };
    if (dark) {
      // Keep all data/formatters and series colors; adapt analytical labels and grid lines.
      for (const key of ['xAxis', 'yAxis']) {
        const axes = option[key];
        if (!axes) continue;
        const adapt = (value: unknown) => {
          const axis = value as Record<string, unknown>;
          return ({ ...axis,
          axisLabel: { ...(axis.axisLabel as object), color: '#c8dbd5' },
          nameTextStyle: { ...(axis.nameTextStyle as object), color: '#c8dbd5' },
          splitLine: { ...(axis.splitLine as object), lineStyle: { color: '#314942' } },
          axisLine: { ...(axis.axisLine as object), lineStyle: { color: '#597369' } },
        }); };
        themed[key] = Array.isArray(axes) ? axes.map(adapt) : adapt(axes);
      }
      const legend = (value: unknown) => {
        const item = (value ?? {}) as Record<string, unknown>;
        return { ...item, textStyle: { ...(item.textStyle as object), color: '#dcebe5' } };
      };
      themed.legend = Array.isArray(option.legend) ? option.legend.map(legend) : legend(option.legend);
    }
    chart.setOption(themed);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option, dark]);

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
