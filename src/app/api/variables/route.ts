import { connection } from "next/server";
import { fail, json } from "@/lib/http";
import { getVariables } from "@/lib/services/data";

// GET /api/variables -> catalog with plain-language definitions
export async function GET() {
  await connection(); // always run at request time
  try {
    return json({ variables: await getVariables(), minYear: 1981 }, 200, 3600);
  } catch (e) {
    return fail(e);
  }
}
