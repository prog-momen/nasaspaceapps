import { connection } from "next/server";
import { fail, json } from "@/lib/http";
import { getExamples } from "@/lib/services/data";

// GET /api/examples -> guided demo investigations
export async function GET() {
  await connection(); // always run at request time
  try {
    return json({ examples: await getExamples() }, 200, 3600);
  } catch (e) {
    return fail(e);
  }
}
