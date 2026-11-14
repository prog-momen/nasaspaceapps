import { connection } from "next/server";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { fail, json, queryShape } from "@/lib/http";
import { resolveRegion } from "@/lib/services/data";

// GET /api/regions/resolve?lat=31.9&lon=35.9[&name=Amman]
// Called when a user clicks the globe or picks a search result. Returns the
// region record (name, country, snapped grid coordinates) for the sidebar.
export async function GET(req: NextRequest) {
  await connection(); // always run at request time
  try {
    const p = z
      .object({ lat: queryShape.lat, lon: queryShape.lon, name: queryShape.name })
      .parse(Object.fromEntries(req.nextUrl.searchParams));
    return json({ region: await resolveRegion(p.lat, p.lon, p.name ? { name: p.name } : undefined) });
  } catch (e) {
    return fail(e);
  }
}
