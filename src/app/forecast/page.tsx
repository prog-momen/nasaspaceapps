import type { Metadata } from "next";
import ForecastView from "@/components/ForecastView";

export const metadata: Metadata = { title: "Forecast - Astro EARTH" };

export default function ForecastPage() {
  return <ForecastView />;
}
