import type { ReactNode } from "react";

import { Header } from "./header";
import { Sidebar } from "./sidebar";

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-shell__workspace">
        <Header />
        <main className="app-shell__content">{children}</main>
      </div>
    </div>
  );
}
