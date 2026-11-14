import { getAdmin } from "../supabase";
import { VARIABLES, EXAMPLES, type VariableDef, type ExampleDef } from "../catalog";
import { fetchPowerMonthly, POWER_FIRST_YEAR } from "../nasa/power";
import { regionKey, snap, reverseGeocode } from "../geo";
import { analyzeTrend, deseasonalize, toPoints, type Point } from "../stats/trend";
import { forecast } from "../stats/forecast";
import { chartExplanations, forecastSummary, trendSummary } from "./insights";

const CACHE_TTL_MS = 30 * 24 * 3600 * 1000;

// Percent change is meaningless for interval scales such as degrees Celsius.
const isRatioScale = (v: VariableDef) => v.unit !== "C";

export class NotFoundError extends Error {}

export interface Query {
  lat: number;
  lon: number;
  variable: string;
  start: number;
  end: number;
  name?: string;
}

export const currentYear = () => new Date().getUTCFullYear();

export async function getVariables(): Promise<VariableDef[]> {
  const db = getAdmin();
  if (db) {
    const { data, error } = await db.from("variables").select("*").eq("active", true).order("sort_order");
    if (!error && data?.length) return data as VariableDef[];
  }
  return VARIABLES;
}

export async function getVariable(key: string): Promise<VariableDef> {
  const v = (await getVariables()).find((x) => x.key === key);
  if (!v) throw new NotFoundError(`Unknown variable "${key}".`);
  return v;
}

export async function getExamples(): Promise<ExampleDef[]> {
  const db = getAdmin();
  if (db) {
    const { data, error } = await db.from("demo_examples").select("*").order("sort_order");
    if (!error && data?.length) return data as ExampleDef[];
  }
  return EXAMPLES;
}

export interface RegionInfo {
  key: string;
  name: string;
  country: string | null;
  country_code: string | null;
  kind: string;
  lat: number;
  lon: number;
}

/** Find or create the region row for a coordinate (shared by click and search). */
export async function resolveRegion(
  lat: number,
  lon: number,
  hint?: { name?: string; country?: string | null; country_code?: string | null; kind?: string },
): Promise<RegionInfo> {
  const key = regionKey(lat, lon);
  const db = getAdmin();
  if (db) {
    const { data } = await db.from("regions").select("*").eq("key", key).maybeSingle();
    if (data && !hint?.name) return data as RegionInfo;
  }
  let name = hint?.name;
  let country = hint?.country ?? null;
  let country_code = hint?.country_code ?? null;
  if (!name) {
    const rev = await reverseGeocode(lat, lon);
    name = rev?.name ?? `${snap(lat).toFixed(1)}, ${snap(lon).toFixed(1)}`;
    country = rev?.country ?? null;
    country_code = rev?.country_code ?? null;
  }
  const row: RegionInfo = {
    key, name, country, country_code, kind: hint?.kind ?? "point",
    lat: snap(lat), lon: snap(lon),
  };
  if (db) await db.from("regions").upsert(row, { onConflict: "key", ignoreDuplicates: !hint?.name });
  return row;
}

async function getSeries(q: Query, v: VariableDef): Promise<Point[]> {
  const key = regionKey(q.lat, q.lon);
  const db = getAdmin();
  const where = { region_key: key, variable_key: v.key, start_year: q.start, end_year: q.end };
  if (db) {
    const { data } = await db.from("timeseries_cache").select("data,fetched_at").match(where).maybeSingle();
    if (data && Date.now() - new Date(data.fetched_at).getTime() < CACHE_TTL_MS) {
      return toPoints(data.data as [string, number][]);
    }
  }
  const entries = await fetchPowerMonthly(snap(q.lat), snap(q.lon), v.provider_param, q.start, q.end);
  if (db && entries.length) {
    await db.from("timeseries_cache").upsert({ ...where, data: entries, fetched_at: new Date().toISOString() });
  }
  return toPoints(entries);
}

async function log(session: string | undefined, key: string, variable: string, action: string) {
  const db = getAdmin();
  if (db) await db.from("investigations").insert({ session_id: session ?? null, region_key: key, variable_key: variable, action });
}

export function validateYears(start: number, end: number) {
  if (start < POWER_FIRST_YEAR) throw new RangeError(`start must be ${POWER_FIRST_YEAR} or later.`);
  if (end > currentYear()) throw new RangeError(`end cannot be after ${currentYear()}.`);
  if (end - start < 4) throw new RangeError("Choose a period of at least 5 years.");
}

export async function getTimeseries(q: Query) {
  validateYears(q.start, q.end);
  const v = await getVariable(q.variable);
  const region = await resolveRegion(q.lat, q.lon, q.name ? { name: q.name } : undefined);
  const points = await getSeries(q, v);
  return { region, variable: v, points: points.map((p) => [p.date, p.value] as [string, number]) };
}

export async function getAnalysis(q: Query, session?: string) {
  validateYears(q.start, q.end);
  const v = await getVariable(q.variable);
  const region = await resolveRegion(q.lat, q.lon, q.name ? { name: q.name } : undefined);
  const points = await getSeries(q, v);
  const trend = analyzeTrend(points);
  if (!isRatioScale(v)) trend.percentChange = null;
  const { climatology, anomalies } = deseasonalize(points);
  const climMean = climatology.reduce((s, x) => s + x, 0) / 12;

  const series = points.map((p, i) => ({
    date: p.date,
    value: p.value,
    anomaly: anomalies[i],
    trend: climMean + trend.ols.intercept + trend.ols.slopePerYear * p.t,
  }));

  const db = getAdmin();
  const result = {
    region, variable: v, query: { start: q.start, end: q.end },
    trend, series,
    summary: trendSummary(trend, v, region.name),
    charts: chartExplanations(trend, v),
    source: {
      provider: "NASA POWER (MERRA-2 / CERES)",
      url: "https://power.larc.nasa.gov/",
      note: "Monthly values for the 0.5 degree grid cell containing the selected point.",
    },
  };
  if (db) {
    await db.from("analyses").upsert(
      {
        region_key: region.key, variable_key: v.key, start_year: q.start, end_year: q.end,
        verdict: trend.verdict, slope_per_year: trend.ols.slopePerYear,
        p_value_ols: trend.ols.pValue, p_value_mk: trend.mannKendall.pValue,
        result: { trend, summary: result.summary },
      },
      { onConflict: "region_key,variable_key,start_year,end_year" },
    );
  }
  await log(session, region.key, v.key, "analyze");
  return result;
}

export async function getForecast(q: Query, horizonYears: number, session?: string) {
  validateYears(q.start, q.end);
  const v = await getVariable(q.variable);
  const region = await resolveRegion(q.lat, q.lon, q.name ? { name: q.name } : undefined);
  const points = await getSeries(q, v);
  const trend = analyzeTrend(points);
  const fc = forecast(points, horizonYears);
  if (!isRatioScale(v)) fc.expectedChange.percent = null;

  const result = {
    region, variable: v, query: { start: q.start, end: q.end, horizonYears },
    historical: points.map((p) => [p.date, p.value] as [string, number]),
    forecast: fc,
    trend: {
      slopePerYear: trend.ols.slopePerYear,
      verdict: trend.verdict,
      olsPValue: trend.ols.pValue,
      mannKendallPValue: trend.mannKendall.pValue,
    },
    summary: forecastSummary(fc, trend, v, region.name),
    media: null as null | { audioUrl?: string; videoUrl?: string }, // reserved for narrated results
  };
  const db = getAdmin();
  if (db) {
    await db.from("forecasts").upsert(
      {
        region_key: region.key, variable_key: v.key, start_year: q.start, end_year: q.end,
        horizon_years: horizonYears, result: { forecast: fc, summary: result.summary },
      },
      { onConflict: "region_key,variable_key,start_year,end_year,horizon_years" },
    );
  }
  await log(session, region.key, v.key, "forecast");
  return result;
}
