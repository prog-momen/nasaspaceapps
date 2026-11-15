import type { Metadata } from "next";
import { Suspense } from "react";
import DashboardView from "@/components/DashboardView";

export const metadata: Metadata = { title: "Dashboard - Astro EARTH" };

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardView />
    </Suspense>
  );
}

