import { z } from "zod";
import { AI_SERVICE_URL, unavailable } from "@/lib/assistant/server";

export const maxDuration = 100;

const ymd = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const schema = z.object({
  message: z.string().trim().min(1).max(1500),
  session_id: z.string().max(128).nullish(),
  controls: z
    .object({
      point: z.object({ lat: z.number().min(-90).max(90), lon: z.number().min(-180).max(180) }).nullish(),
      bbox: z.array(z.number()).length(4).nullish(),
      start: ymd.nullish(),
      end: ymd.nullish(),
      task: z.string().max(40).nullish(),
      variable: z.string().max(60).nullish(),
      provider: z.string().max(40).nullish(),
      answer_mode: z.enum(["auto", "template"]).nullish(),
      language: z.enum(["ar", "en"]).nullish(),
    })
    .nullish(),
  conflict_choice: z.enum(["message", "controls"]).nullish(),
});

// Drop null/undefined keys so the Python side sees only what the user set.
function clean<T>(v: T): T {
  if (Array.isArray(v)) return v as T;
  if (v && typeof v === "object") {
    return Object.fromEntries(
      Object.entries(v).filter(([, x]) => x !== null && x !== undefined).map(([k, x]) => [k, clean(x)]),
    ) as T;
  }
  return v;
}

// POST /api/assistant/chat -> proxies to the Python AI service (never exposed to the browser)
export async function POST(req: Request) {
  let body: z.infer<typeof schema>;
  try {
    body = schema.parse(await req.json());
  } catch (e) {
    const details = e instanceof z.ZodError ? e.issues.map((i) => `${i.path.join(".")}: ${i.message}`) : ["invalid JSON"];
    return Response.json({ error: "invalid_request", details }, { status: 400 });
  }
  try {
    const res = await fetch(`${AI_SERVICE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(clean(body)),
      cache: "no-store",
      signal: AbortSignal.timeout(95_000),
    });
    const data = await res.json().catch(() => null);
    if (!data || typeof data !== "object") return unavailable(`AI service returned HTTP ${res.status} without JSON.`);
    delete (data as Record<string, unknown>).raw_result;
    return Response.json(data, { status: res.ok ? 200 : res.status >= 500 ? 502 : res.status });
  } catch (e) {
    const timedOut = e instanceof Error && (e.name === "TimeoutError" || e.name === "AbortError");
    return unavailable(timedOut ? "The AI service took too long to answer." : "The AI service is unreachable.");
  }
}
