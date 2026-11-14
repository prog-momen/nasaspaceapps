import { connection } from "next/server";
import type { NextRequest } from "next/server";
import { fail, json, querySchema } from "@/lib/http";
import { getTimeseries } from "@/lib/services/data";

// GET /api/timeseries?lat&lon&variable&start&end -> raw monthly series
export async function GET(req: NextRequest) {
  await connection(); // always run at request time
  try {
    const q = querySchema.parse(Object.fromEntries(req.nextUrl.searchParams));
    return json(await getTimeseries(q), 200, 3600);
  } catch (e) {
    return fail(e);
  }
}
