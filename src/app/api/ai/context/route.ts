import { connection } from "next/server";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { fail, json, queryShape, sessionId } from "@/lib/http";
import { getAnalysis, getForecast } from "@/lib/services/data";

const schema = z.object({ ...queryShape, horizon: z.coerce.number().int().min(1).max(30).optional() });

/**
 * GET /api/ai/context?lat&lon&variable&start&end[&horizon]
 * Integration point for the separate AI Assistant service. Returns compact,
 * grounded facts (numbers and plain-language summaries) the LLM can quote
 * without recomputing anything. When AI_CONTEXT_TOKEN is set, callers must
 * send `Authorization: Bearer <token>`.
 */
export async function GET(req: NextRequest) {
  await connection(); // always run at request time
  try {
    const token = process.env.AI_CONTEXT_TOKEN;
    if (token && req.headers.get("authorization") !== `Bearer ${token}`) {
      return json({ error: "unauthorized" }, 401);
    }
    const { horizon, ...q } = schema.parse(Object.fromEntries(req.nextUrl.searchParams));
    const session = sessionId(req);
    const a = await getAnalysis(q, session);
    const t = a.trend;
    const f = horizon ? await getForecast(q, horizon, session) : null;
    return json({
      region: { name: a.region.name, country: a.region.country, lat: a.region.lat, lon: a.region.lon },
      variable: {
        key: a.variable.key,
        name: a.variable.name,
        unit: a.variable.unit,
        definition: a.variable.definition,
        why_it_matters: a.variable.why_it_matters,
      },
      period: t.period,
      facts: {
        direction: t.direction,
        verdict: t.verdict,
        slope_per_year: t.ols.slopePerYear,
        slope_ci95: t.ols.ci95,
        sen_slope_per_year: t.mannKendall.senSlopePerYear,
        p_value_regression: t.ols.pValue,
        p_value_mann_kendall: t.mannKendall.pValue,
        total_change: t.totalChange,
        percent_change: t.percentChange,
        mean: t.mean,
        min: t.min,
        max: t.max,
      },
      summary: a.summary,
      forecast: f && {
        horizon_years: f.query.horizonYears,
        method: f.forecast.method,
        expected_change: f.forecast.expectedChange,
        annual: f.forecast.annualForecast,
        backtest: f.forecast.backtest,
        summary: f.summary,
        caveats: f.forecast.caveats,
      },
      source: a.source,
    });
  } catch (e) {
    return fail(e);
  }
}
