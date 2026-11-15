import type { AssistantResponse } from "./types";

const VAR_TO_DASH: Record<string, string> = {
  air_temperature: "T2M",
  precipitation: "PRECTOTCORR",
  relative_humidity: "RH2M",
  wind_speed: "WS10M",
};

export function dashboardKey(pythonVariable?: string | null): string | undefined {
  return pythonVariable ? VAR_TO_DASH[pythonVariable] : undefined;
}

function build(path: string, r: AssistantResponse, extra?: Record<string, string>): string | null {
  const loc = r.resolved?.location;
  if (!loc || !Number.isFinite(loc.latitude) || !Number.isFinite(loc.longitude)) return null;
  const p = new URLSearchParams({
    lat: String(loc.latitude),
    lon: String(loc.longitude),
    name: loc.name || `${loc.latitude.toFixed(1)}, ${loc.longitude.toFixed(1)}`,
  });
  const v = dashboardKey(r.resolved?.variable);
  if (v) p.set("variable", v);
  const per = r.resolved?.period;
  if (per?.start_year && per?.end_year) {
    p.set("start", String(per.start_year));
    p.set("end", String(per.end_year));
  }
  for (const [k, val] of Object.entries(extra ?? {})) p.set(k, val);
  return `${path}?${p}`;
}

export const dashboardHref = (r: AssistantResponse) => build("/dashboard", r);

export function forecastHref(r: AssistantResponse): string | null {
  if (!r.tools?.some((t) => t.name === "forecast_monthly")) return null;
  return build("/forecast", r, { horizon: "1" });
}
