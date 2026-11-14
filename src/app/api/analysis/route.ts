import { connection } from "next/server";
import type { NextRequest } from "next/server";
import { fail, json, querySchema, sessionId } from "@/lib/http";
import { getAnalysis } from "@/lib/services/data";

// GET /api/analysis?lat&lon&variable&start&end
// Dashboard payload: series, trend stats, significance tests, chart explanations.
export async function GET(req: NextRequest) {
  await connection(); // always run at request time
  try {
    const q = querySchema.parse(Object.fromEntries(req.nextUrl.searchParams));
    return json(await getAnalysis(q, sessionId(req)));
  } catch (e) {
    return fail(e);
  }
}
