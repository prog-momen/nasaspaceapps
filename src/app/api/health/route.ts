import { connection } from "next/server";
import { getAdmin } from "@/lib/supabase";

export async function GET() {
  await connection(); // always run at request time
  const db = getAdmin();
  let database: "not_configured" | "ok" | "error" = "not_configured";
  if (db) {
    const { error } = await db.from("variables").select("key", { head: true, count: "exact" });
    database = error ? "error" : "ok";
  }
  return Response.json({ status: "ok", database });
}
