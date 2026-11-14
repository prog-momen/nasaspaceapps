import { connection } from "next/server";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { fail, json } from "@/lib/http";
import { searchPlaces } from "@/lib/geo";
import { getAdmin } from "@/lib/supabase";

// GET /api/regions/search?q=amman  -> countries/cities/regions with coordinates
export async function GET(req: NextRequest) {
  await connection(); // always run at request time
  try {
    const { q } = z
      .object({ q: z.string().trim().min(2).max(80) })
      .parse(Object.fromEntries(req.nextUrl.searchParams));
    const results = await searchPlaces(q);
    // Make sure seeded countries match even if the geocoder ranks a city first.
    const db = getAdmin();
    if (db) {
      const { data } = await db
        .from("regions")
        .select("name,country,country_code,kind,lat,lon")
        .eq("kind", "country")
        .ilike("name", `${q.replace(/[%_]/g, "")}%`)
        .limit(3);
      for (const c of data ?? []) {
        if (!results.some((r) => r.kind === "country" && r.country_code === c.country_code)) {
          results.unshift({ ...c, admin1: null, population: null });
        }
      }
    }
    return json({ query: q, results }, 200, 3600);
  } catch (e) {
    return fail(e);
  }
}
