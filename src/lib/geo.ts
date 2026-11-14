// Geocoding helpers backed by free, key-less services.

export interface GeoResult {
  name: string;
  country: string | null;
  country_code: string | null;
  admin1: string | null;
  kind: "country" | "city" | "region";
  lat: number;
  lon: number;
  population: number | null;
}

/** POWER's source grid is ~0.5 degrees, so we snap points to it for caching. */
export const snap = (v: number) => Math.round(v * 2) / 2;
export const regionKey = (lat: number, lon: number) =>
  `${snap(lat).toFixed(1)},${snap(lon).toFixed(1)}`;

export async function searchPlaces(q: string, limit = 8): Promise<GeoResult[]> {
  const url = new URL("https://geocoding-api.open-meteo.com/v1/search");
  url.searchParams.set("name", q);
  url.searchParams.set("count", String(limit));
  url.searchParams.set("language", "en");
  const res = await fetch(url, { signal: AbortSignal.timeout(10_000) });
  if (!res.ok) return [];
  const json = await res.json();
  type Row = {
    name: string; country?: string; country_code?: string; admin1?: string;
    feature_code?: string; latitude: number; longitude: number; population?: number;
  };
  return ((json.results ?? []) as Row[]).map((r) => ({
    name: r.name,
    country: r.country ?? null,
    country_code: r.country_code ?? null,
    admin1: r.admin1 ?? null,
    kind: r.feature_code?.startsWith("PCL")
      ? "country"
      : r.feature_code?.startsWith("ADM")
        ? "region"
        : "city",
    lat: r.latitude,
    lon: r.longitude,
    population: r.population ?? null,
  }));
}

/** Best-effort place name for a clicked coordinate; null if unavailable. */
export async function reverseGeocode(
  lat: number,
  lon: number,
): Promise<{ name: string; country: string | null; country_code: string | null } | null> {
  try {
    const url = new URL("https://api.bigdatacloud.net/data/reverse-geocode-client");
    url.searchParams.set("latitude", String(lat));
    url.searchParams.set("longitude", String(lon));
    url.searchParams.set("localityLanguage", "en");
    const res = await fetch(url, { signal: AbortSignal.timeout(8_000) });
    if (!res.ok) return null;
    const j = await res.json();
    const name = j.city || j.locality || j.principalSubdivision || j.countryName || j.localityInfo?.informative?.[0]?.name;
    if (!name) return null;
    return { name, country: j.countryName || null, country_code: j.countryCode || null };
  } catch {
    return null;
  }
}
