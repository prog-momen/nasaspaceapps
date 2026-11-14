// Seeds reference data into Supabase: variable catalog, demo examples, countries.
// Usage: npm run db:seed   (needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local)
import { createClient } from "@supabase/supabase-js";
import { VARIABLES, EXAMPLES } from "../src/lib/catalog.ts";

const url = process.env.SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !key) {
  console.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY.");
  process.exit(1);
}
const db = createClient(url, key, { auth: { persistSession: false } });

const snap = (v: number) => Math.round(v * 2) / 2;

async function must<T extends { error: { message: string } | null }>(label: string, p: PromiseLike<T>) {
  const res = await p;
  if (res.error) throw new Error(`${label}: ${res.error.message}`);
  console.log(`ok  ${label}`);
}

await must("variables", db.from("variables").upsert(VARIABLES, { onConflict: "key" }));

await must(
  "demo_examples",
  db.from("demo_examples").upsert(EXAMPLES, { onConflict: "slug" }),
);

// Country list from the open mledoze/countries dataset (country-level centroids).
const res = await fetch("https://raw.githubusercontent.com/mledoze/countries/master/countries.json");
if (!res.ok) throw new Error(`countries dataset HTTP ${res.status}`);
type C = { name: { common: string }; cca2: string; latlng: [number, number]; region: string };
const countries = (await res.json()) as C[];
const rows = countries
  .filter((c) => Array.isArray(c.latlng) && c.latlng.length === 2 && c.region !== "Antarctic")
  .map((c) => ({
    key: `${snap(c.latlng[0]).toFixed(1)},${snap(c.latlng[1]).toFixed(1)}`,
    name: c.name.common,
    country: c.name.common,
    country_code: c.cca2,
    kind: "country",
    lat: c.latlng[0],
    lon: c.latlng[1],
  }));

// Two countries can snap to the same 0.5 degree cell; keep the first per key.
const seen = new Set<string>();
const unique = rows.filter((r) => (seen.has(r.key) ? false : (seen.add(r.key), true)));
await must(`regions (${unique.length} countries)`, db.from("regions").upsert(unique, { onConflict: "key" }));
console.log("Done.");
