// Client for the NASA POWER API (monthly, point). POWER serves MERRA-2 and
// CERES derived variables for any latitude/longitude with no API key.
// Docs: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/

const BASE = "https://power.larc.nasa.gov/api/temporal/monthly/point";
export const POWER_FIRST_YEAR = 1981;

export class UpstreamError extends Error {}

export async function fetchPowerMonthly(
  lat: number,
  lon: number,
  param: string,
  startYear: number,
  endYear: number,
): Promise<[string, number][]> {
  const url = new URL(BASE);
  url.searchParams.set("parameters", param);
  url.searchParams.set("community", "AG");
  url.searchParams.set("latitude", String(lat));
  url.searchParams.set("longitude", String(lon));
  url.searchParams.set("start", String(startYear));
  url.searchParams.set("end", String(endYear));
  url.searchParams.set("format", "JSON");

  let res: Response;
  try {
    res = await fetch(url, { signal: AbortSignal.timeout(60_000), cache: "no-store" });
  } catch {
    throw new UpstreamError("NASA POWER did not respond in time.");
  }
  if (!res.ok) {
    throw new UpstreamError(`NASA POWER returned HTTP ${res.status}.`);
  }
  const json = await res.json();
  const raw: Record<string, number> | undefined = json?.properties?.parameter?.[param];
  if (!raw) throw new UpstreamError("NASA POWER returned no data for this request.");
  const fill: number = json?.header?.fill_value ?? -999;

  const out: [string, number][] = [];
  for (const [key, value] of Object.entries(raw)) {
    const month = Number(key.slice(4));
    if (month < 1 || month > 12) continue; // "13" is POWER's annual mean
    if (value === fill || !Number.isFinite(value)) continue;
    out.push([`${key.slice(0, 4)}-${key.slice(4)}`, value]);
  }
  return out.sort((a, b) => a[0].localeCompare(b[0]));
}
