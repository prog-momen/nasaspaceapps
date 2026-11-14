// Browser-side helpers for the backend. Types are imported type-only so no
// server code is bundled into the client.
import type { getAnalysis, getForecast } from "./services/data";
import type { VariableDef } from "./catalog";

export type AnalysisResult = Awaited<ReturnType<typeof getAnalysis>>;
export type ForecastPageResult = Awaited<ReturnType<typeof getForecast>>;
export type { VariableDef };

/** Everything the user picked on the home page; carried in the URL. */
export interface Selection {
  lat: number;
  lon: number;
  name: string;
  variable: string;
  start: number;
  end: number;
}

export const MIN_YEAR = 1981;
export const DEFAULT_VARIABLE = "T2M";
export const currentYear = () => new Date().getFullYear();
export const defaultStart = () => 1990;
// Last complete year, so the default period has no partial-year gaps.
export const defaultEnd = () => currentYear() - 1;

export function selectionToParams(s: Selection): URLSearchParams {
  return new URLSearchParams({
    lat: String(s.lat),
    lon: String(s.lon),
    name: s.name,
    variable: s.variable,
    start: String(s.start),
    end: String(s.end),
  });
}

export function parseSelection(p: URLSearchParams): Selection | null {
  const lat = Number(p.get("lat"));
  const lon = Number(p.get("lon"));
  if (!p.get("lat") || !p.get("lon") || !Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return {
    lat,
    lon,
    name: p.get("name") ?? `${lat.toFixed(1)}, ${lon.toFixed(1)}`,
    variable: p.get("variable") ?? DEFAULT_VARIABLE,
    start: Number(p.get("start")) || defaultStart(),
    end: Number(p.get("end")) || defaultEnd(),
  };
}

export class ApiError extends Error {}

async function get<T>(path: string, params: URLSearchParams): Promise<T> {
  const res = await fetch(`${path}?${params}`);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      body.message ?? body.details?.join(", ") ?? "Something went wrong. Please try again.",
    );
  }
  return body as T;
}

export const fetchVariables = () =>
  get<{ variables: VariableDef[]; minYear: number }>("/api/variables", new URLSearchParams());

export const fetchAnalysis = (s: Selection) => get<AnalysisResult>("/api/analysis", selectionToParams(s));

export const fetchForecast = (s: Selection, horizon: number) => {
  const p = selectionToParams(s);
  p.set("horizon", String(horizon));
  return get<ForecastPageResult>("/api/forecast", p);
};
