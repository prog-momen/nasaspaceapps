import { connection } from "next/server";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { fail, json } from "@/lib/http";
import { getAdmin } from "@/lib/supabase";

// GET /api/regions/browse?kind=country&filter=jo&page=1&pageSize=300
export async function GET(req: NextRequest) {
  await connection(); // always run at request time
  try {
    const p = z
      .object({
        kind: z.enum(["country", "city", "region", "point"]).default("country"),
        filter: z.string().max(60).optional(),
        page: z.coerce.number().int().min(1).default(1),
        pageSize: z.coerce.number().int().min(1).max(300).default(300),
      })
      .parse(Object.fromEntries(req.nextUrl.searchParams));
    const db = getAdmin();
    if (!db) {
      return json(
        { error: "database_not_configured", message: "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, then run npm run db:seed." },
        503,
      );
    }
    let query = db
      .from("regions")
      .select("name,country,country_code,kind,lat,lon", { count: "exact" })
      .eq("kind", p.kind)
      .order("name");
    if (p.filter) query = query.ilike("name", `%${p.filter.replace(/[%_]/g, "")}%`);
    const from = (p.page - 1) * p.pageSize;
    const { data, count, error } = await query.range(from, from + p.pageSize - 1);
    if (error) throw error;
    return json({ total: count ?? 0, page: p.page, items: data }, 200, 3600);
  } catch (e) {
    return fail(e);
  }
}
