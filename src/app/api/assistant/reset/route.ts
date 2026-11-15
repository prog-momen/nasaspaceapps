import { z } from "zod";
import { AI_SERVICE_URL, unavailable } from "@/lib/assistant/server";


const schema = z.object({ session_id: z.string().min(1).max(128) });

// POST /api/assistant/reset {session_id}
export async function POST(req: Request) {
  const parsed = schema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return Response.json({ error: "invalid_request" }, { status: 400 });
  try {
    const res = await fetch(`${AI_SERVICE_URL}/api/chat/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed.data),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    return Response.json({ ok: res.ok }, { status: res.ok ? 200 : 502 });
  } catch {
    return unavailable("The AI service is unreachable.");
  }
}
