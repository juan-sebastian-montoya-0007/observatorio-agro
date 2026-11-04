import type { ReactNode } from "react";

import { Header } from "./header";
import { Sidebar } from "./sidebar";
import { AssistantWidget } from "../assistant/assistant-widget";
import { MotionSurface } from "./motion-surface";
import "./liquid-glass.css";
import "./dark-theme.css";

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MotionSurface><div className="app-shell">
      <Sidebar />
      <div className="app-shell__workspace">
        <Header />
        <main className="app-shell__content">{children}</main>
      </div>
      <AssistantWidget />
    </div></MotionSurface>
  );
}
