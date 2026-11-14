import type { Metadata } from "next";
import ForecastView from "@/components/ForecastView";

export const metadata: Metadata = { title: "Forecast - EarthTrend Explorer" };

export default function ForecastPage() {
  return <ForecastView />;
}
