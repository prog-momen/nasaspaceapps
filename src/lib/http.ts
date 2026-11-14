import { z } from "zod";
import { NotFoundError, currentYear } from "./services/data";
import { UpstreamError } from "./nasa/power";
import { InsufficientDataError } from "./stats/trend";

const num = z.coerce.number();

export const queryShape = {
  lat: num.min(-90).max(90),
  lon: num.min(-180).max(180),
  variable: z.string().min(1).max(40),
  start: num.int().default(1990),
  end: num.int().default(currentYear()),
  name: z.string().max(120).optional(),
};
export const querySchema = z.object(queryShape);

export function json(data: unknown, status = 200, maxAgeSeconds = 0) {
  return Response.json(data, {
    status,
    headers: maxAgeSeconds
      ? { "Cache-Control": `public, s-maxage=${maxAgeSeconds}, stale-while-revalidate=${maxAgeSeconds * 4}` }
      : undefined,
  });
}

export function fail(err: unknown) {
  if (err instanceof z.ZodError) {
    return json({ error: "invalid_request", details: err.issues.map((i) => `${i.path.join(".")}: ${i.message}`) }, 400);
  }
  if (err instanceof RangeError) return json({ error: "invalid_request", message: err.message }, 400);
  if (err instanceof NotFoundError) return json({ error: "not_found", message: err.message }, 404);
  if (err instanceof InsufficientDataError) return json({ error: "insufficient_data", message: err.message }, 422);
  if (err instanceof UpstreamError) return json({ error: "upstream_unavailable", message: err.message }, 502);
  console.error(err);
  return json({ error: "internal_error" }, 500);
}

export const sessionId = (req: Request) => req.headers.get("x-session-id")?.slice(0, 64) ?? undefined;
