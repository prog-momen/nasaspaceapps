import type { Metadata } from "next";
import { Suspense } from "react";
import DashboardView from "@/components/DashboardView";

export const metadata: Metadata = { title: "Dashboard - EarthTrend Explorer" };

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardView />
    </Suspense>
  );
}

