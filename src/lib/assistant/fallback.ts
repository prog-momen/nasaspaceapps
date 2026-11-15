// Offline grounded mode: used ONLY when the AI service proxy answers 503.
// Keyword-picks a variable and quotes the deterministic /api/ai/context facts.
import { COUNTRIES } from "@/data/countries";
import type { ChatItem } from "./types";

export const OFFLINE_LABEL = "Offline grounded mode (AI service unavailable)";

export function detectSuggestedVariable(query: string) {
  const q = query.toLowerCase();
  const has = (...w: string[]) => w.some((x) => q.includes(x));
  if (has("rain", "precip", "storm", "flood", "مطر", "أمطار", "هطول"))
    return { key: "PRECTOTCORR", name: "Precipitation", reason: "Rain & snowfall observation" };
  if (has("max", "heat", "summer", "hot", "حر", "موجة حارة", "أعلى حرارة"))
    return { key: "T2M_MAX", name: "Maximum Air Temperature", reason: "Daytime extreme heat analysis" };
  if (has("min", "night", "cold", "frost", "صقيع", "برد", "أدنى حرارة"))
    return { key: "T2M_MIN", name: "Minimum Air Temperature", reason: "Nighttime cooling and frost recovery" };
  if (has("surface", "skin", "ground", "سطح"))
    return { key: "TS", name: "Surface Skin Temperature", reason: "Direct thermal satellite skin observation" };
  if (has("drought", "soil", "root", "crop", "farm", "جفاف", "تربة"))
    return { key: "GWETROOT", name: "Root Zone Soil Wetness", reason: "Early indicator of agricultural drought" };
  if (has("evap", "تبخر")) return { key: "EVLAND", name: "Evaporation from Land", reason: "Hydrological water loss" };
  if (has("humid", "رطوبة")) return { key: "RH2M", name: "Relative Humidity", reason: "Atmospheric moisture level" };
  if (has("wind", "gust", "speed", "رياح", "عاصف")) return { key: "WS10M", name: "Wind Speed (10m)", reason: "Surface wind kinetics" };
  if (has("cloud", "overcast", "غيم", "سحاب")) return { key: "CLOUD_AMT", name: "Cloud Amount", reason: "Sky coverage fraction" };
  if (has("solar", "sun", "radiation", "energy", "شمس", "طاقة"))
    return { key: "ALLSKY_SFC_SW_DWN", name: "Solar Radiation at Surface", reason: "Incident solar energy" };
  if (has("pressure", "barometer", "ضغط")) return { key: "PS", name: "Surface Pressure", reason: "Atmospheric air mass" };
  return { key: "T2M", name: "Air Temperature (2m)", reason: "Baseline thermal trend observation" };
}

export async function offlineReply(
  query: string,
  selected?: { lat: number; lon: number; name: string } | null,
): Promise<Pick<ChatItem, "text" | "dashboardLink" | "offline">> {
  // Default is the Levant, never 0,0.
  let lat = 31.95;
  let lon = 35.23;
  let name = selected?.name || "Palestine (Default Baseline)";
  const coord = query.match(/(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)/);
  if (coord && Math.abs(+coord[1]) <= 90 && Math.abs(+coord[2]) <= 180) {
    lat = +coord[1];
    lon = +coord[2];
    name = `Grid Cell (${Math.abs(lat).toFixed(1)}°${lat >= 0 ? "N" : "S"}, ${Math.abs(lon).toFixed(1)}°${lon >= 0 ? "E" : "W"})`;
  } else {
    const ql = query.toLowerCase();
    const c = COUNTRIES.find(
      (x) => ql.includes(x.name.toLowerCase()) || ql.includes(x.code3.toLowerCase()) || ql.includes(x.capital.toLowerCase()),
    );
    if (c) {
      lat = c.lat;
      lon = c.lng;
      name = c.name;
    } else if (selected) {
      lat = selected.lat;
      lon = selected.lon;
      name = selected.name;
    }
  }
  const v = detectSuggestedVariable(query);
  try {
    const res = await fetch(`/api/ai/context?lat=${lat}&lon=${lon}&variable=${v.key}&start=1990&end=2024&horizon=10`);
    if (!res.ok) {
      return {
        offline: true,
        text: `${OFFLINE_LABEL}\n\nNo observational data returned for "${query}" (HTTP ${res.status}). No simulated data is provided.`,
      };
    }
    const d = await res.json();
    const region = d.region?.name || name;
    const unit = d.variable?.unit || "";
    const p = d.facts?.p_value_mann_kendall;
    let text = `${OFFLINE_LABEL}\n\n**NASA grounded investigation: ${region}**\n`;
    text += `- **Suggested variable:** ${d.variable?.name || v.name} (${v.reason})\n`;
    text += `- **Verdict:** ${d.facts?.verdict || "Observation completed"}\n`;
    if (d.facts?.slope_per_year) text += `- **Rate of change (slope):** ${(d.facts.slope_per_year * 10).toFixed(3)} ${unit}/decade\n`;
    if (d.facts?.total_change) text += `- **Total change:** ${d.facts.total_change > 0 ? "+" : ""}${d.facts.total_change.toFixed(2)} ${unit}\n`;
    if (p !== undefined) text += `- **Mann-Kendall p-value:** ${p}\n`;
    return { offline: true, text, dashboardLink: { lat, lon, name: region, variable: v.key } };
  } catch {
    return { offline: true, text: `${OFFLINE_LABEL}\n\nThe data backend is unreachable too. No simulated data is returned.` };
  }
}
