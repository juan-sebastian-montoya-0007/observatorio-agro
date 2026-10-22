import { Suspense } from "react";

import { DashboardLoading } from "@/components/common/async-state";
import { Dashboard } from "@/components/dashboard/dashboard";
import { AppShell } from "@/components/layout/app-shell";

export default function HomePage() {
  return (
    <AppShell>
      <Suspense fallback={<DashboardLoading />}>
        <Dashboard />
      </Suspense>
    </AppShell>
  );
}
