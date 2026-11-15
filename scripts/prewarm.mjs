// Warms the analysis/forecast cache for every demo example before a live demo.
// Usage: node scripts/prewarm.mjs [baseUrl]   (default http://localhost:3000)
const base = (process.argv[2] ?? "http://localhost:3000").replace(/\/$/, "");

async function call(label, path) {
  const t0 = Date.now();
  try {
    const res = await fetch(base + path, { signal: AbortSignal.timeout(180_000) });
    const body = await res.json().catch(() => ({}));
    const note = res.ok ? "" : ` ${body.error ?? body.message ?? ""}`;
    console.log(`${res.ok ? "OK  " : "FAIL"} ${res.status} ${((Date.now() - t0) / 1000).toFixed(1)}s ${label}${note}`);
    return res.ok ? body : null;
  } catch (e) {
    console.log(`FAIL --- ${((Date.now() - t0) / 1000).toFixed(1)}s ${label} ${e.message}`);
    return null;
  }
}

const data = await call("/api/examples", "/api/examples");
const examples = data?.examples ?? [];
if (!examples.length) {
  console.log("No examples returned; is the dev server running at " + base + "?");
  process.exit(1);
}

let failed = 0;
for (const ex of examples) {
  const p = new URLSearchParams({
    lat: String(ex.lat),
    lon: String(ex.lon),
    name: ex.region_name ?? ex.title ?? "",
    variable: ex.variable_key,
    start: String(ex.start_year),
    end: String(ex.end_year),
  });
  const name = ex.slug ?? ex.region_name;
  if (!(await call(`analysis ${name}`, `/api/analysis?${p}`))) failed++;
  p.set("horizon", "5");
  if (!(await call(`forecast ${name}`, `/api/forecast?${p}`))) failed++;
}
console.log(failed ? `Done with ${failed} failure(s).` : "Done: all calls succeeded.");
process.exit(failed ? 1 : 0);
