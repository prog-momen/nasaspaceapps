import { deseasonalize, ols, type Point } from "./trend";
import { tCritical } from "./special";

export interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
}

export interface Backtest {
  holdoutMonths: number;
  modelMae: number;
  modelRmse: number;
  baselineMae: number; // seasonal climatology without trend
  baselineRmse: number;
  beatsBaseline: boolean;
}

export interface ForecastResult {
  method: string;
  description: string;
  horizonYears: number;
  horizonMonths: number;
  /** Date the forecast was issued (today). The requested span starts in this month. */
  issueDate: string;
  /** Months between the last NASA data month and today: no data exists yet, so they are forecast too. */
  gapMonths: string[];
  forecast: ForecastPoint[];
  annualForecast: { year: number; mean: number; lower: number; upper: number }[];
  expectedChange: { fromLastYearMean: number; toFinalYearMean: number; absolute: number; percent: number | null };
  backtest: Backtest | null;
  caveats: string[];
}

interface Fit {
  a: number;
  b: number;
  climatology: number[];
  sigma: number;
  n: number;
  tBar: number;
  sxx: number;
}

function fit(points: Point[]): Fit {
  const { climatology, anomalies } = deseasonalize(points);
  const x = points.map((p) => p.t);
  const r = ols(x, anomalies);
  const n = x.length;
  const tBar = x.reduce((s, v) => s + v, 0) / n;
  const sxx = x.reduce((s, v) => s + (v - tBar) ** 2, 0);
  const sse = anomalies.reduce(
    (s, y, i) => s + (y - (r.intercept + r.slopePerYear * x[i])) ** 2,
    0,
  );
  return {
    a: r.intercept,
    b: r.slopePerYear,
    climatology,
    sigma: Math.sqrt(sse / Math.max(1, n - 2)),
    n,
    tBar,
    sxx,
  };
}

function predict(f: Fit, t: number, month: number) {
  const value = f.climatology[month - 1] + f.a + f.b * t;
  const se = f.sigma * Math.sqrt(1 + 1 / f.n + (t - f.tBar) ** 2 / f.sxx);
  const half = tCritical(Math.max(1, f.n - 2)) * se;
  return { value, lower: value - half, upper: value + half };
}

function nextMonths(last: Point, count: number) {
  const out: { date: string; t: number; month: number; year: number }[] = [];
  let y = last.year;
  let m = last.month;
  for (let i = 0; i < count; i++) {
    m += 1;
    if (m > 12) {
      m = 1;
      y += 1;
    }
    out.push({
      date: `${y}-${String(m).padStart(2, "0")}`,
      t: y + (m - 0.5) / 12,
      month: m,
      year: y,
    });
  }
  return out;
}

function backtest(points: Point[]): Backtest | null {
  const holdout = Math.min(60, Math.floor(points.length * 0.2));
  if (holdout < 12 || points.length - holdout < 60) return null;
  const train = points.slice(0, points.length - holdout);
  const test = points.slice(points.length - holdout);
  const f = fit(train);
  let mae = 0;
  let se = 0;
  let bMae = 0;
  let bSe = 0;
  for (const p of test) {
    const model = predict(f, p.t, p.month).value;
    const base = f.climatology[p.month - 1] + (f.a + f.b * f.tBar);
    mae += Math.abs(p.value - model);
    se += (p.value - model) ** 2;
    bMae += Math.abs(p.value - base);
    bSe += (p.value - base) ** 2;
  }
  const n = test.length;
  return {
    holdoutMonths: n,
    modelMae: mae / n,
    modelRmse: Math.sqrt(se / n),
    baselineMae: bMae / n,
    baselineRmse: Math.sqrt(bSe / n),
    beatsBaseline: se < bSe,
  };
}

/**
 * Forecast = linear trend on deseasonalized anomalies + repeating seasonal
 * cycle, with 95% prediction intervals that widen away from the data.
 * It is a statistical extrapolation of the past, not a climate model run.
 */
export function forecast(points: Point[], horizonYears: number, today: Date = new Date()): ForecastResult {
  const last = points[points.length - 1];
  // The requested span is counted from TODAY. Months between the last data month and the current month have no NASA data yet,
  // so they are forecast as well and reported as gap months.
  const d = Math.max(0, today.getUTCFullYear() * 12 + (today.getUTCMonth() + 1) - (last.year * 12 + last.month));
  const horizonMonths = d + Math.round(horizonYears * 12);
  const f = fit(points);
  const future = nextMonths(last, horizonMonths);
  const gapMonths = future.slice(0, Math.max(0, d - 1)).map((p) => p.date);
  const fc: ForecastPoint[] = future.map((p) => {
    const r = predict(f, p.t, p.month);
    return { date: p.date, value: r.value, lower: r.lower, upper: r.upper };
  });

  const byYear = new Map<number, { v: number[]; lo: number[]; hi: number[] }>();
  future.forEach((p, i) => {
    const e = byYear.get(p.year) ?? { v: [], lo: [], hi: [] };
    e.v.push(fc[i].value);
    e.lo.push(fc[i].lower);
    e.hi.push(fc[i].upper);
    byYear.set(p.year, e);
  });
  const avg = (a: number[]) => a.reduce((s, v) => s + v, 0) / a.length;
  const annualForecast = [...byYear.entries()]
    .filter(([, e]) => e.v.length === 12)
    .map(([year, e]) => ({ year, mean: avg(e.v), lower: avg(e.lo), upper: avg(e.hi) }));

  const lastYear = points[points.length - 1].year;
  const recent = points.filter((p) => p.year === lastYear - 1 || p.year === lastYear).map((p) => p.value);
  const fromMean = avg(recent.length ? recent : points.slice(-12).map((p) => p.value));
  const toMean = annualForecast.length
    ? annualForecast[annualForecast.length - 1].mean
    : avg(fc.slice(-12).map((p) => p.value));

  return {
    method: "linear_trend_plus_seasonal_cycle",
    description:
      "The model removes the repeating seasonal cycle, fits a straight-line trend to what is left (ordinary least squares), then adds the seasonal cycle back for future months. The shaded band is a 95% prediction interval.",
    horizonYears,
    horizonMonths,
    issueDate: today.toISOString().slice(0, 10),
    gapMonths,
    forecast: fc,
    annualForecast,
    expectedChange: {
      fromLastYearMean: fromMean,
      toFinalYearMean: toMean,
      absolute: toMean - fromMean,
      percent: Math.abs(fromMean) > 1e-9 ? ((toMean - fromMean) / Math.abs(fromMean)) * 100 : null,
    },
    backtest: backtest(points),
    caveats: [
      "Assumes the historical linear trend continues unchanged.",
      "Does not model non-linear changes, tipping points or El Nino style cycles.",
      "Uncertainty grows the further ahead you look.",
      "Annual bands are the average of monthly 95% prediction intervals, so they are wider than the uncertainty of a yearly average.",
    ],
  };
}
