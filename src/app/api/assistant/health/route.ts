import { connection } from "next/server";
import { AI_SERVICE_URL } from "@/lib/assistant/server";


// GET /api/assistant/health -> { available, problems[] }
export async function GET() {
  await connection(); // always run at request time
  try {
    const res = await fetch(`${AI_SERVICE_URL}/api/rag/health`, { cache: "no-store", signal: AbortSignal.timeout(4_000) });
    const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    const problems: string[] = Array.isArray(data.problems) ? data.problems.map(String) : [];
    if (!res.ok) problems.push(`AI service health check returned HTTP ${res.status}`);
    // "degraded" (e.g. no LLM key) still answers via templates, so the service counts as available.
    const available = res.ok;
    return Response.json({ available, problems });
  } catch {
    return Response.json({ available: false, problems: ["AI service is unreachable"] });
  }
}
