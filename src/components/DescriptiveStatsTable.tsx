"use client";

import React, { useState } from "react";
import { fmt, fmtP, signed } from "./PageFrame";

interface Props {
  series: { date: string; value: number }[];
  trend: {
    mean: number;
    stdDev: number;
    min: { date: string; value: number };
    max: { date: string; value: number };
    ols: {
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
    };
    mannKendall: {
      n: number;
      s: number;
      z: number;
      pValue: number;
      tau: number;
      senSlopePerYear: number;
      senCi95: [number, number];
    };
    period: { start: string; end: string; months: number; years: number };
    totalChange: number;
    direction: "increasing" | "decreasing" | "flat";
  };
  unit: string;
}

function quantile(sorted: number[], q: number): number {
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
}

type MomentKey = "mean" | "median" | "stdDev" | "range" | "iqr" | "r2";

export default function DescriptiveStatsTable({ series, trend, unit }: Props) {
  const [selectedMoment, setSelectedMoment] = useState<MomentKey>("mean");
  const [applyAutocorr, setApplyAutocorr] = useState<boolean>(true);

  const values = series.map((s) => s.value);
  const sorted = [...values].sort((a, b) => a - b);
  const n = values.length;

  const variance = trend.stdDev * trend.stdDev;
  const rangeVal = trend.max.value - trend.min.value;
  const q1 = quantile(sorted, 0.25);
  const median = quantile(sorted, 0.5);
  const q3 = quantile(sorted, 0.75);
  const iqr = q3 - q1;

  const moments: {
    key: MomentKey;
    label: string;
    value: string;
    subtitle: string;
    explanation: string;
  }[] = [
    {
      key: "mean",
      label: "Mean (μ)",
      value: `${fmt(trend.mean)} ${unit}`,
      subtitle: "Baseline average",
      explanation: `The arithmetic mean across all ${n} monthly observations from ${trend.period.start} to ${trend.period.end}. Represents the historical central tendency.`,
    },
    {
      key: "median",
      label: "Median (50th %)",
      value: `${fmt(median)} ${unit}`,
      subtitle: "Middle value",
      explanation: `The 50th percentile rank. Because median (${fmt(median)}) is close to mean (${fmt(trend.mean)}), the observational distribution shows minimal skewness.`,
    },
    {
      key: "stdDev",
      label: "Std Dev (σ)",
      value: `±${fmt(trend.stdDev)} ${unit}`,
      subtitle: `Variance ${fmt(variance)}`,
      explanation: `Standard deviation measures average seasonal and weather departure from the mean. Variance equals ${fmt(variance)} ${unit}².`,
    },
    {
      key: "range",
      label: "Full Range",
      value: `${fmt(rangeVal)} ${unit}`,
      subtitle: `${fmt(trend.min.value)} to ${fmt(trend.max.value)}`,
      explanation: `Total observational span between the absolute historical minimum (${fmt(trend.min.value)} in ${trend.min.date}) and maximum (${fmt(trend.max.value)} in ${trend.max.date}).`,
    },
    {
      key: "iqr",
      label: "Interquartile (IQR)",
      value: `${fmt(iqr)} ${unit}`,
      subtitle: `Q1 ${fmt(q1)} / Q3 ${fmt(q3)}`,
      explanation: `The spread of the middle 50% of monthly observations (25th percentile Q1 = ${fmt(q1)}, 75th percentile Q3 = ${fmt(q3)}). Robust against extreme climate outliers.`,
    },
    {
      key: "r2",
      label: "R² Coefficient",
      value: `${(trend.ols.r2 * 100).toFixed(1)}%`,
      subtitle: `R² = ${trend.ols.r2.toFixed(3)}`,
      explanation: `Proportion of deseasonalized anomaly variance explained by the linear trend line. In environmental systems, values above 15% signify strong systematic drift over noise.`,
    },
  ];

  const activeMomentData = moments.find((m) => m.key === selectedMoment) || moments[0];

  return (
    <div className="h-full flex flex-col justify-between select-none">
      {/* Top Telemetry Header & Interactive Metric Pills (Zero Cards) */}
      <div className="flex flex-col gap-2 border-b border-white/10 pb-2 shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#8b5cf6]/20 text-[#a78bfa] border border-[#8b5cf6]/40 font-bold uppercase">
            Descriptive Moments & Verification Matrix
          </span>
          <span className="text-xs text-[#9ca3af] font-mono">
            Span: {trend.period.start} to {trend.period.end} ({n} observations)
          </span>
        </div>

        {/* 6 Interactive Clickable Metric Buttons */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {moments.map((m) => {
            const isSel = selectedMoment === m.key;
            return (
              <button
                key={m.key}
                onClick={() => setSelectedMoment(m.key)}
                className={`p-2 rounded-lg text-left transition-all border cursor-pointer ${
                  isSel
                    ? "bg-[#2563eb]/30 border-blue-400 text-white shadow-[0_0_12px_rgba(37,99,235,0.4)]"
                    : "bg-white/5 border-white/10 text-[#a1a1aa] hover:bg-white/10 hover:text-white"
                }`}
              >
                <span className="text-[9.5px] uppercase tracking-wider block opacity-75 truncate">{m.label}</span>
                <span className="text-sm font-bold font-mono text-white block mt-0.5 truncate">{m.value}</span>
                <span className="text-[9px] text-[#6b7280] block truncate">{m.subtitle}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Dynamic Inspector for the Selected Metric */}
      <div className="py-2 px-3 bg-white/5 rounded-lg border border-white/10 flex flex-wrap items-center justify-between gap-2 text-xs shrink-0 my-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#38bdf8]"></span>
          <span className="font-bold text-white font-mono">{activeMomentData.label}: {activeMomentData.value}</span>
          <span className="text-[#cbd5e1] text-[11px]">— {activeMomentData.explanation}</span>
        </div>
        <span className="text-[10px] text-[#9ca3af] italic">Click any metric above to inspect</span>
      </div>

      {/* Center Telemetry Data Table: Parametric vs Non-Parametric (Borderless Columns) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-1 flex-1 min-h-0 text-xs">
        {/* Left Column: Parametric OLS Regression */}
        <div className="border-r border-white/10 pr-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-white/10">
              <span className="font-bold text-[#60a5fa] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#60a5fa]"></span>
                Parametric OLS Regression (t-test)
              </span>
              <button
                onClick={() => setApplyAutocorr((prev) => !prev)}
                className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
                  applyAutocorr
                    ? "bg-[#2563eb]/20 border-blue-400 text-blue-300 font-bold"
                    : "bg-white/5 border-white/10 text-[#9ca3af]"
                }`}
                title="Toggle serial correlation inflation of standard error"
              >
                Autocorr Correction: {applyAutocorr ? "ACTIVE" : "OFF"}
              </button>
            </div>

            <table className="w-full">
              <tbody className="divide-y divide-white/5 text-[#cbd5e1]">
                <tr>
                  <td className="py-1 text-[#9ca3af]">Decadal Rate (Slope)</td>
                  <td className="py-1 text-right font-mono font-bold text-white">
                    {signed(trend.ols.slopePerYear * 10, 3)} {unit} / decade
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Annual Rate</td>
                  <td className="py-1 text-right font-mono">
                    {signed(trend.ols.slopePerYear, 4)} {unit} / year
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Standard Error of Slope (SE)</td>
                  <td className="py-1 text-right font-mono">
                    ±{fmt((applyAutocorr ? trend.ols.stdErr : trend.ols.stdErr * Math.sqrt(trend.ols.effectiveN / trend.ols.n)) * 10, 4)} {unit}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Student&apos;s t-Statistic</td>
                  <td className="py-1 text-right font-mono">
                    t = {fmt(trend.ols.tStat, 3)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Two-Sided p-value</td>
                  <td className="py-1 text-right font-mono font-bold text-[#34d399]">
                    {fmtP(trend.ols.pValue)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Lag-1 Autocorrelation (r₁)</td>
                  <td className="py-1 text-right font-mono">
                    {trend.ols.lag1Autocorr.toFixed(3)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Effective Sample Size (N_eff)</td>
                  <td className="py-1 text-right font-mono text-[#fbbf24]">
                    {applyAutocorr ? Math.round(trend.ols.effectiveN) : trend.ols.n} of {trend.ols.n} months
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="text-[10px] text-[#6b7280] mt-1">
            Accounts for persistence between consecutive monthly values to prevent inflated t-statistics.
          </p>
        </div>

        {/* Right Column: Non-Parametric Mann-Kendall */}
        <div className="flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-white/10">
              <span className="font-bold text-[#34d399] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#34d399]"></span>
                Non-Parametric Mann-Kendall Rank Test
              </span>
              <span className="text-[10px] font-mono text-[#9ca3af]">
                Annual Mean Aggregates
              </span>
            </div>

            <table className="w-full">
              <tbody className="divide-y divide-white/5 text-[#cbd5e1]">
                <tr>
                  <td className="py-1 text-[#9ca3af]">Sen&apos;s Median Slope</td>
                  <td className="py-1 text-right font-mono font-bold text-white">
                    {signed(trend.mannKendall.senSlopePerYear * 10, 3)} {unit} / decade
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">95% Interval</td>
                  <td className="py-1 text-right font-mono">
                    {fmt(trend.mannKendall.senCi95[0] * 10, 3)} to {fmt(trend.mannKendall.senCi95[1] * 10, 3)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Kendall&apos;s Tau Correlation (τ)</td>
                  <td className="py-1 text-right font-mono">
                    τ = {trend.mannKendall.tau.toFixed(3)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Mann-Kendall S-Score</td>
                  <td className="py-1 text-right font-mono">
                    S = {trend.mannKendall.s}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Standard Normal z-score</td>
                  <td className="py-1 text-right font-mono">
                    z = {trend.mannKendall.z.toFixed(2)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Mann-Kendall p-value</td>
                  <td className="py-1 text-right font-mono font-bold text-[#34d399]">
                    {fmtP(trend.mannKendall.pValue)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-[#9ca3af]">Annual Sample Years Analyzed</td>
                  <td className="py-1 text-right font-mono text-[#fbbf24]">
                    {trend.mannKendall.n} complete years
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="text-[10px] text-[#6b7280] mt-1">
            Distribution-free rank test on annual means; completely immune to seasonal distortion and outlier skew.
          </p>
        </div>
      </div>

      {/* Bottom Telemetry Strip: Historical Extremes */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/10 text-xs shrink-0 font-mono">
        <div className="flex items-center gap-3">
          <span className="text-[#9ca3af]">Historical Minimum:</span>
          <span className="font-bold text-[#38bdf8]">{fmt(trend.min.value)} {unit}</span>
          <span className="text-[#6b7280]">({trend.min.date})</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[#9ca3af]">Historical Maximum:</span>
          <span className="font-bold text-[#f87171]">{fmt(trend.max.value)} {unit}</span>
          <span className="text-[#6b7280]">({trend.max.date})</span>
        </div>
      </div>
    </div>
  );
}
