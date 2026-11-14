import { connection } from "next/server";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { fail, json, queryShape, sessionId } from "@/lib/http";
import { getForecast } from "@/lib/services/data";

const schema = z.object({ ...queryShape, horizon: z.coerce.number().int().min(1).max(30).default(5) });

// GET /api/forecast?lat&lon&variable&start&end&horizon=5
export async function GET(req: NextRequest) {
  await connection(); // always run at request time
  try {
    const { horizon, ...q } = schema.parse(Object.fromEntries(req.nextUrl.searchParams));
    return json(await getForecast(q, horizon, sessionId(req)));
  } catch (e) {
    return fail(e);
  }
}
