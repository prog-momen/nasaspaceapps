import { normalCdf, tCritical, tTwoSidedP } from "./special";

/** One monthly observation. `t` is the decimal year at mid-month. */
export interface Point {
  date: string; // YYYY-MM
  year: number;
  month: number; // 1..12
  t: number;
  value: number;
}

export interface OlsResult {
  slopePerYear: number;
  intercept: number;
  stdErr: number;
  tStat: number;
  pValue: number;
  ci95: [number, number];
  r2: number;
  n: number;
  effectiveN: number;
  lag1Autocorr: number;
}

export interface MannKendallResult {
  n: number;
  s: number;
  z: number;
  pValue: number;
  tau: number;
  direction: "increasing" | "decreasing" | "none";
  senSlopePerYear: number;
  senCi95: [number, number];
}

export type Verdict = "significant" | "weak_evidence" | "not_significant";

export interface TrendAnalysis {
  alpha: number;
  period: { start: string; end: string; months: number; years: number };
  mean: number;
  stdDev: number;
  min: { date: string; value: number };
  max: { date: string; value: number };
  /** Linear trend fitted on deseasonalized monthly anomalies (t-test, CI). */
  ols: OlsResult;
  /** Non-parametric test on annual mean anomalies. */
  mannKendall: MannKendallResult;
  totalChange: number; // slope * span in the variable's unit
  percentChange: number | null;
  direction: "increasing" | "decreasing" | "flat";
  verdict: Verdict;
  seasonalClimatology: number[]; // 12 values, Jan..Dec
  annual: { year: number; mean: number; months: number }[];
}

const mean = (a: number[]) => a.reduce((s, v) => s + v, 0) / a.length;

function stdDev(a: number[]): number {
  if (a.length < 2) return 0;
  const m = mean(a);
  return Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / (a.length - 1));
}

function median(sorted: number[]): number {
  const n = sorted.length;
  if (n === 0) return NaN;
  const mid = Math.floor(n / 2);
  return n % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function toPoints(entries: [string, number][]): Point[] {
  return entries
    .map(([date, value]) => {
      const year = Number(date.slice(0, 4));
      const month = Number(date.slice(5, 7));
      return { date, year, month, t: year + (month - 0.5) / 12, value };
    })
    .sort((a, b) => a.t - b.t);
}

/** Monthly climatology (mean per calendar month) and the anomalies from it. */
export function deseasonalize(points: Point[]) {
  const buckets: number[][] = Array.from({ length: 12 }, () => []);
  for (const p of points) buckets[p.month - 1].push(p.value);
  const climatology = buckets.map((b) => (b.length ? mean(b) : 0));
  const anomalies = points.map((p) => p.value - climatology[p.month - 1]);
  return { climatology, anomalies };
}

export function annualMeans(points: Point[], values: number[], minMonths = 9) {
  const byYear = new Map<number, number[]>();
  points.forEach((p, i) => {
    const arr = byYear.get(p.year) ?? [];
    arr.push(values[i]);
    byYear.set(p.year, arr);
  });
  return [...byYear.entries()]
    .filter(([, v]) => v.length >= minMonths)
    .map(([year, v]) => ({ year, mean: mean(v), months: v.length }))
    .sort((a, b) => a.year - b.year);
}

function lag1(residuals: number[]): number {
  const m = mean(residuals);
  let num = 0;
  let den = 0;
  for (let i = 0; i < residuals.length; i++) {
    den += (residuals[i] - m) ** 2;
    if (i > 0) num += (residuals[i] - m) * (residuals[i - 1] - m);
  }
  return den === 0 ? 0 : num / den;
}

/**
 * Ordinary least squares y = a + b*x. Monthly anomalies are autocorrelated, so
 * the standard error is inflated using the effective sample size
 * n_eff = n (1 - r1) / (1 + r1) to avoid over-stating significance.
 */
export function ols(x: number[], y: number[]): OlsResult {
  const n = x.length;
  const mx = mean(x);
  const my = mean(y);
  let sxx = 0;
  let sxy = 0;
  let syy = 0;
  for (let i = 0; i < n; i++) {
    sxx += (x[i] - mx) ** 2;
    sxy += (x[i] - mx) * (y[i] - my);
    syy += (y[i] - my) ** 2;
  }
  const slope = sxy / sxx;
  const intercept = my - slope * mx;
  const resid = y.map((v, i) => v - (intercept + slope * x[i]));
  const sse = resid.reduce((s, r) => s + r * r, 0);
  const r1 = Math.max(0, Math.min(0.95, lag1(resid)));
  const nEff = Math.max(3, (n * (1 - r1)) / (1 + r1));
  const df = Math.max(1, nEff - 2);
  // Residual variance with the effective degrees of freedom.
  const s2 = sse / Math.max(1, n - 2);
  const se = Math.sqrt((s2 * ((n - 2) / df)) / sxx);
  const tStat = se === 0 ? 0 : slope / se;
  const crit = tCritical(df);
  return {
    slopePerYear: slope,
    intercept,
    stdErr: se,
    tStat,
    pValue: tTwoSidedP(tStat, df),
    ci95: [slope - crit * se, slope + crit * se],
    r2: syy === 0 ? 0 : 1 - sse / syy,
    n,
    effectiveN: nEff,
    lag1Autocorr: r1,
  };
}

/** Mann-Kendall trend test (tie-corrected) with Sen's slope and its 95% CI. */
export function mannKendall(
  x: number[],
  y: number[],
  alpha = 0.05,
): MannKendallResult {
  const n = y.length;
  let s = 0;
  const slopes: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    for (let j = i + 1; j < n; j++) {
      s += Math.sign(y[j] - y[i]);
      slopes.push((y[j] - y[i]) / (x[j] - x[i]));
    }
  }
  const counts = new Map<number, number>();
  for (const v of y) counts.set(v, (counts.get(v) ?? 0) + 1);
  let tieTerm = 0;
  for (const c of counts.values()) {
    if (c > 1) tieTerm += c * (c - 1) * (2 * c + 5);
  }
  const varS = (n * (n - 1) * (2 * n + 5) - tieTerm) / 18;
  const z = s > 0 ? (s - 1) / Math.sqrt(varS) : s < 0 ? (s + 1) / Math.sqrt(varS) : 0;
  const p = 2 * (1 - normalCdf(Math.abs(z)));
  slopes.sort((a, b) => a - b);
  const sen = median(slopes);
  const N = slopes.length;
  const zCrit = Math.abs(inverseNormal(1 - alpha / 2));
  const c = zCrit * Math.sqrt(varS);
  const lo = Math.max(0, Math.floor((N - c) / 2));
  const hi = Math.min(N - 1, Math.ceil((N + c) / 2));
  return {
    n,
    s,
    z,
    pValue: p,
    tau: s / ((n * (n - 1)) / 2),
    direction: p < alpha ? (s > 0 ? "increasing" : "decreasing") : "none",
    senSlopePerYear: sen,
    senCi95: [slopes[lo], slopes[hi]],
  };
}

// Acklam's rational approximation of the inverse normal CDF.
function inverseNormal(p: number): number {
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const lowP = 0.02425;
  if (p < lowP) {
    const q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p > 1 - lowP) return -inverseNormal(1 - p);
  const q = p - 0.5;
  const r = q * q;
  return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) /
    (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

export class InsufficientDataError extends Error {}

export function analyzeTrend(points: Point[], alpha = 0.05): TrendAnalysis {
  if (points.length < 36) {
    throw new InsufficientDataError(
      "At least 36 monthly observations (3 years) are needed to detect a trend.",
    );
  }
  const { climatology, anomalies } = deseasonalize(points);
  const x = points.map((p) => p.t);
  const olsRes = ols(x, anomalies);

  const annualAnom = annualMeans(points, anomalies);
  if (annualAnom.length < 5) {
    throw new InsufficientDataError(
      "At least 5 years with 9+ valid months are needed for the Mann-Kendall test.",
    );
  }
  const mk = mannKendall(
    annualAnom.map((a) => a.year + 0.5),
    annualAnom.map((a) => a.mean),
    alpha,
  );

  const values = points.map((p) => p.value);
  const minIdx = values.indexOf(Math.min(...values));
  const maxIdx = values.indexOf(Math.max(...values));
  const span = points[points.length - 1].t - points[0].t;
  const totalChange = olsRes.slopePerYear * span;
  const m = mean(values);

  const olsSig = olsRes.pValue < alpha;
  const mkSig = mk.pValue < alpha;
  const verdict: Verdict =
    olsSig && mkSig ? "significant" : olsSig || mkSig ? "weak_evidence" : "not_significant";

  return {
    alpha,
    period: {
      start: points[0].date,
      end: points[points.length - 1].date,
      months: points.length,
      years: Math.round(span * 10) / 10,
    },
    mean: m,
    stdDev: stdDev(values),
    min: { date: points[minIdx].date, value: values[minIdx] },
    max: { date: points[maxIdx].date, value: values[maxIdx] },
    ols: olsRes,
    mannKendall: mk,
    totalChange,
    percentChange: Math.abs(m) > 1e-9 ? (totalChange / Math.abs(m)) * 100 : null,
    direction:
      olsRes.slopePerYear === 0 ? "flat" : olsRes.slopePerYear > 0 ? "increasing" : "decreasing",
    verdict,
    seasonalClimatology: climatology,
    annual: annualMeans(points, values, 12),
  };
}
