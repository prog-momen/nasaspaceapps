// Server-only helpers shared by the /api/assistant/* proxy routes.
export const AI_SERVICE_URL = (process.env.AI_SERVICE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export function unavailable(message: string) {
  return Response.json({ error: "assistant_unavailable", message }, { status: 503 });
}
