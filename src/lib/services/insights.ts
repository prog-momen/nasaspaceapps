import type { TrendAnalysis } from "../stats/trend";
import type { ForecastResult } from "../stats/forecast";
import type { VariableDef } from "../catalog";

const fmt = (v: number, d = 2) =>
  Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(d);
const pfmt = (p: number) => (p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(3)}`);

export function trendSummary(t: TrendAnalysis, v: VariableDef, region: string): string[] {
  const dir = t.direction === "increasing" ? "rising" : t.direction === "decreasing" ? "falling" : "flat";
  const rate = `${fmt(Math.abs(t.ols.slopePerYear), 3)} ${v.unit} per year`;
  const decade = `${fmt(Math.abs(t.ols.slopePerYear) * 10)} ${v.unit} per decade`;
  const lines = [
    `${v.name} in ${region} is ${dir} at about ${rate} (${decade}) between ${t.period.start} and ${t.period.end}.`,
    `Over ${t.period.years} years that adds up to ${t.totalChange >= 0 ? "+" : "-"}${fmt(Math.abs(t.totalChange))} ${v.unit}${
      t.percentChange === null ? "" : ` (${t.percentChange >= 0 ? "+" : ""}${t.percentChange.toFixed(1)}% of the average)`
    }.`,
  ];
  if (t.verdict === "significant") {
    lines.push(
      `Both tests agree the trend is statistically significant (regression ${pfmt(t.ols.pValue)}, Mann-Kendall ${pfmt(t.mannKendall.pValue)}), so it is unlikely to be random variation.`,
    );
  } else if (t.verdict === "weak_evidence") {
    lines.push(
      `The tests disagree (regression ${pfmt(t.ols.pValue)}, Mann-Kendall ${pfmt(t.mannKendall.pValue)}). There is some sign of a trend but not enough to call it significant. A longer record could settle it.`,
    );
  } else {
    lines.push(
      `Neither test finds a significant trend (regression ${pfmt(t.ols.pValue)}, Mann-Kendall ${pfmt(t.mannKendall.pValue)}). The change we see could be natural variability.`,
    );
  }
  return lines;
}

export interface ChartExplanation {
  id: string;
  title: string;
  what: string;
  why: string;
  inference: string;
}

export function chartExplanations(t: TrendAnalysis, v: VariableDef): ChartExplanation[] {
  const warm = t.direction === "increasing";
  return [
    {
      id: "timeseries",
      title: "Monthly time series with trend line",
      what: `Each point is the monthly average of ${v.name.toLowerCase()}. The straight line is the fitted linear trend.`,
      why: "A long, regular record is needed before any statistical claim about change is meaningful.",
      inference: `The line slopes ${warm ? "upward" : t.direction === "decreasing" ? "downward" : "almost flat"}; the repeating wave is the seasonal cycle, not the trend.`,
    },
    {
      id: "anomalies",
      title: "Deseasonalized anomalies",
      what: "The same data after subtracting the typical value for each calendar month.",
      why: "Seasons are much larger than long-term change and hide it. Removing them isolates the signal.",
      inference: "Bars above zero are warmer/higher than normal for that month; a drift of bars over time is the trend.",
    },
    {
      id: "annual",
      title: "Annual averages",
      what: "One value per complete year.",
      why: "Averaging a full year cancels the season and smooths noise, which is what the Mann-Kendall test uses.",
      inference: `Compare early and late years to see the change by eye; the highest year was around ${t.annual.length ? t.annual.reduce((a, b) => (b.mean > a.mean ? b : a)).year : "n/a"}.`,
    },
    {
      id: "seasonal",
      title: "Seasonal cycle",
      what: "The average value for each month of the year across the whole period.",
      why: "Shows the normal rhythm that anomalies are measured against.",
      inference: "Peaks and troughs show which months drive the variable; a trend may be stronger in some seasons.",
    },
    {
      id: "significance",
      title: "Significance tests",
      what: "A regression t-test and the Mann-Kendall test, each with a p-value, plus Sen's slope and a 95% confidence interval.",
      why: "A visible slope is not proof. A small p-value (below 0.05) says the slope is unlikely to be chance.",
      inference: `Here the verdict is "${t.verdict.replace("_", " ")}". If the confidence interval excludes zero, the direction of change is supported.`,
    },
  ];
}

export function forecastSummary(f: ForecastResult, t: TrendAnalysis, v: VariableDef, region: string): string[] {
  const e = f.expectedChange;
  const sign = e.absolute >= 0 ? "+" : "-";
  const lines = [
    `If the historical trend continues, ${v.name.toLowerCase()} in ${region} is projected to change by ${sign}${fmt(Math.abs(e.absolute))} ${v.unit} over the next ${f.horizonYears} year${f.horizonYears > 1 ? "s" : ""}${
      e.percent === null ? "" : ` (${e.percent >= 0 ? "+" : ""}${e.percent.toFixed(1)}%)`
    }.`,
  ];
  if (t.verdict !== "significant") {
    lines.push("The underlying trend is not statistically significant, so treat this projection with caution.");
  }
  if (f.backtest) {
    lines.push(
      f.backtest.beatsBaseline
        ? `In a hold-out test on the last ${f.backtest.holdoutMonths} months, including the trend reduced error versus using the seasonal average alone (RMSE ${fmt(f.backtest.modelRmse)} vs ${fmt(f.backtest.baselineRmse)} ${v.unit}).`
        : `In a hold-out test on the last ${f.backtest.holdoutMonths} months, the trend did not beat the plain seasonal average (RMSE ${fmt(f.backtest.modelRmse)} vs ${fmt(f.backtest.baselineRmse)} ${v.unit}), so the trend adds little predictive skill here.`,
    );
  }
  return lines;
}
