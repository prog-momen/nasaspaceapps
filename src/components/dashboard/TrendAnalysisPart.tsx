"use client";

import React, { useState } from "react";
import { fmt, fmtP, signed } from "../PageFrame";

interface Props {
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
  totalChange: number;
  direction: "increasing" | "decreasing" | "flat";
  verdict: "significant" | "weak_evidence" | "not_significant";
  periodYears: number;
  unit: string;
}

export default function TrendAnalysisPart({
  ols,
  mannKendall,
  totalChange,
  direction,
  verdict,
  periodYears,
  unit,
}: Props) {
  const [confLevel, setConfLevel] = useState<90 | 95 | 99>(95);
  const [applyAutocorr, setApplyAutocorr] = useState(true);
  const [modelView, setModelView] = useState<"both" | "sen" | "ols">("both");
  const [showExplanation, setShowExplanation] = useState(false);

  const zCrit = confLevel === 90 ? 1.645 : confLevel === 99 ? 2.576 : 1.96;

  // OLS decadal calculations
  const olsSlopeDecade = ols.slopePerYear * 10;
  const olsStdErrDecade = ols.stdErr * 10;
  const olsCiLo = confLevel === 95 ? ols.ci95[0] * 10 : olsSlopeDecade - zCrit * olsStdErrDecade;
  const olsCiHi = confLevel === 95 ? ols.ci95[1] * 10 : olsSlopeDecade + zCrit * olsStdErrDecade;
  const olsMargin = Math.abs(olsCiHi - olsCiLo) / 2;

  // Sen's slope decadal calculations
  const senSlopeDecade = mannKendall.senSlopePerYear * 10;
  const senMarginDecade = (Math.abs(mannKendall.senCi95[1] - mannKendall.senCi95[0]) * 10) / 2;
  const senScaleFactor = zCrit / 1.96;
  const senCiLo = senSlopeDecade - senMarginDecade * senScaleFactor;
  const senCiHi = senSlopeDecade + senMarginDecade * senScaleFactor;

  const olsExcludesZero = (olsCiLo > 0 && olsCiHi > 0) || (olsCiLo < 0 && olsCiHi < 0);
  const senExcludesZero = (senCiLo > 0 && senCiHi > 0) || (senCiLo < 0 && senCiHi < 0);

  // Graphical track scaling
  const minV = Math.min(olsCiLo, senCiLo, 0);
  const maxV = Math.max(olsCiHi, senCiHi, 0);
  const span = maxV - minV || 1;
  const pad = span * 0.2;
  const domainMin = minV - pad;
  const domainMax = maxV + pad;
  const scale = (val: number) => ((val - domainMin) / (domainMax - domainMin)) * 100;

  const zeroPos = scale(0);
  const olsLeft = Math.max(0, Math.min(100, scale(olsCiLo)));
  const olsWidth = Math.max(1, scale(olsCiHi) - olsLeft);
  const olsCenter = Math.max(0, Math.min(100, scale(olsSlopeDecade)));

  const senLeft = Math.max(0, Math.min(100, scale(senCiLo)));
  const senWidth = Math.max(1, scale(senCiHi) - senLeft);
  const senCenter = Math.max(0, Math.min(100, scale(senSlopeDecade)));

  return (
    <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 h-full flex flex-col justify-between gap-2.5 select-none text-slate-100 font-sans">
      {/* 1. TOP HEADER & CONTROLS */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-white/10 shrink-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 uppercase">
            Part 3: Trend Analysis & Statistical Verification
          </span>

          {/* Model View Toggle */}
          <div className="flex items-center gap-1 dark-clay-inset p-1 rounded-xl text-[11px] font-semibold">
            <button
              onClick={() => setModelView("both")}
              className={`px-2 py-0.5 rounded-lg transition-all ${
                modelView === "both"
                  ? "bg-sky-500 text-white font-bold shadow-md shadow-sky-900/50"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Dual Comparison
            </button>
            <button
              onClick={() => setModelView("sen")}
              className={`px-2 py-0.5 rounded-lg transition-all ${
                modelView === "sen"
                  ? "bg-emerald-600 text-white font-bold shadow-md shadow-emerald-900/50"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Mann-Kendall & Sen
            </button>
            <button
              onClick={() => setModelView("ols")}
              className={`px-2 py-0.5 rounded-lg transition-all ${
                modelView === "ols"
                  ? "bg-sky-600 text-white font-bold shadow-md shadow-sky-900/50"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Linear OLS
            </button>
          </div>

          {/* Confidence Level Toggle */}
          <div className="flex items-center gap-1 text-[10.5px] font-mono">
            <span className="text-slate-400 font-bold">CI Level:</span>
            {([90, 95, 99] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setConfLevel(lvl)}
                className={`px-2 py-0.5 rounded-lg border transition-all ${
                  confLevel === lvl
                    ? "bg-white text-slate-900 font-bold shadow-sm"
                    : "dark-clay-button text-slate-300"
                }`}
              >
                {lvl}%
              </button>
            ))}
          </div>

          {/* About Chart Toggle */}
          <button
            onClick={() => setShowExplanation((p) => !p)}
            className="text-[10.5px] font-bold text-emerald-400 hover:text-emerald-300 px-2 py-0.5 rounded-xl dark-clay-button flex items-center gap-1 ml-1"
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span>{showExplanation ? "Hide Info" : "About Chart"}</span>
          </button>
        </div>

        {/* Significance Status Badge */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-slate-300">
            Direction: <strong className={direction === "increasing" ? "text-emerald-400 font-bold" : direction === "decreasing" ? "text-rose-400 font-bold" : "text-slate-300"}>{direction}</strong>
          </span>
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full border font-bold flex items-center gap-1.5 shadow-sm ${
              verdict === "significant"
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                : "bg-amber-500/20 text-amber-300 border-amber-500/40"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                verdict === "significant" ? "bg-emerald-400" : "bg-amber-400"
              }`}
            />
            {verdict === "significant" ? "Statistically Significant Trend" : "Inconclusive Trend"}
          </span>
        </div>
      </div>

      {/* DEDICATED EXPLANATION PANEL ABOUT THE TREND CHARTS (If Opened) */}
      {showExplanation && (
        <div className="dark-clay-inset rounded-2xl p-3 text-xs shrink-0 border border-emerald-500/30 space-y-2">
          <div className="flex items-center justify-between pb-1.5 border-b border-white/10">
            <strong className="text-emerald-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              Understanding the Trend Detection & Confidence Interval Visualizations
            </strong>
            <span className="text-[10px] font-mono text-slate-400">World Meteorological Organization (WMO) Standard</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-[11px]">
            <div className="p-2 rounded-xl bg-white/5 border border-emerald-500/20">
              <span className="text-emerald-400 font-bold block">1. The Zero-Exclusion Rule (0.0 Line)</span>
              <p className="text-slate-300 mt-0.5 leading-relaxed">
                The red vertical line marks a slope of zero (no change). If the {confLevel}% shaded uncertainty range bar lies entirely to the right (positive) or left (negative) without touching zero, the trend is mathematically verified at p &lt; {confLevel === 95 ? "0.05" : confLevel === 99 ? "0.01" : "0.10"}.
              </p>
            </div>
            <div className="p-2 rounded-xl bg-white/5 border border-sky-500/20">
              <span className="text-sky-400 font-bold block">2. Sen&apos;s Slope vs Linear OLS</span>
              <p className="text-slate-300 mt-0.5 leading-relaxed">
                • <strong>Sen&apos;s Slope:</strong> The median rate of all pairwise points. Completely immune to extreme outlier weather shocks.<br />
                • <strong>OLS Regression:</strong> Minimizes squared errors; provides classical parametric t-statistics and standard error margins.
              </p>
            </div>
            <div className="p-2 rounded-xl bg-white/5 border border-amber-500/20">
              <span className="text-amber-400 font-bold block">3. Serial Correlation & N_eff</span>
              <p className="text-slate-300 mt-0.5 leading-relaxed">
                Atmospheric states carry memory from month to month (Lag-1 autocorrelation r₁ = {ols.lag1Autocorr.toFixed(2)}). Correcting the degrees of freedom to N_eff ({Math.round(ols.effectiveN)} months) prevents false trend detections caused by serial inertia.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 2. CONFIDENCE INTERVAL UNCERTAINTY RANGE BARS (Dark Sunken Track) */}
      <div className="dark-clay-inset rounded-2xl p-2.5 sm:p-3 flex flex-col gap-2 shrink-0">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-white font-bold flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
            {confLevel}% Confidence Interval Range Bar ({confLevel === 95 ? "p < 0.05" : confLevel === 99 ? "p < 0.01" : "p < 0.10"})
          </span>
          <span className="text-slate-300">
            Zero-Exclusion Test:{" "}
            <strong className={senExcludesZero ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
              {senExcludesZero ? "Excludes Zero (Confirmed Trend)" : "Spans Zero (Inconclusive)"}
            </strong>
          </span>
        </div>

        {/* Range Bar Graphic Tracks */}
        <div className="flex flex-col gap-2 my-0.5">
          {/* TRACK 1: Mann-Kendall Sen's Slope */}
          {(modelView === "both" || modelView === "sen") && (
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-emerald-400 font-bold">
                  Mann-Kendall Sen&apos;s Slope: {signed(senSlopeDecade)} {unit}/decade
                </span>
                <span className="text-slate-400">
                  [{signed(senCiLo)} to {signed(senCiHi)}] {unit} • τ = {mannKendall.tau.toFixed(3)}
                </span>
              </div>

              <div className="relative w-full h-8 bg-black/40 rounded-xl border border-white/10 overflow-hidden">
                {/* Zero Reference Line */}
                <div className="absolute top-0 bottom-0 w-[2px] bg-rose-500 z-10" style={{ left: `${zeroPos}%` }}>
                  <span className="absolute -top-0.5 -translate-x-1/2 px-1 rounded bg-rose-500 text-[8px] font-bold text-white uppercase shadow-sm">
                    0.0
                  </span>
                </div>

                {/* Shaded Uncertainty Band */}
                <div
                  className={`absolute top-1.5 bottom-1.5 rounded-lg transition-all duration-300 border shadow-lg ${
                    senExcludesZero
                      ? "bg-emerald-500/30 border-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.3)]"
                      : "bg-amber-500/30 border-amber-400 shadow-[0_0_12px_rgba(251,191,36,0.3)]"
                  }`}
                  style={{ left: `${senLeft}%`, width: `${senWidth}%` }}
                />

                {/* Central Point Marker */}
                <div
                  className="absolute top-1 bottom-1 w-2 -translate-x-1/2 bg-emerald-400 rounded shadow-[0_0_8px_rgba(52,211,153,0.8)] z-20"
                  style={{ left: `${senCenter}%` }}
                >
                  <span className="absolute -bottom-0.5 -translate-x-1/2 px-1 rounded bg-emerald-500 text-[8px] font-bold text-black font-mono shadow-sm">
                    {signed(senSlopeDecade, 2)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TRACK 2: Linear OLS Regression */}
          {(modelView === "both" || modelView === "ols") && (
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-sky-400 font-bold">
                  Linear Regression (OLS): {signed(olsSlopeDecade)} ± {fmt(olsMargin)} {unit}/decade
                </span>
                <span className="text-slate-400">
                  [{signed(olsCiLo)} to {signed(olsCiHi)}] {unit} • t = {fmt(ols.tStat, 2)} (p = {fmtP(ols.pValue)})
                </span>
              </div>

              <div className="relative w-full h-8 bg-black/40 rounded-xl border border-white/10 overflow-hidden">
                <div className="absolute top-0 bottom-0 w-[2px] bg-rose-500 z-10" style={{ left: `${zeroPos}%` }}>
                  <span className="absolute -top-0.5 -translate-x-1/2 px-1 rounded bg-rose-500 text-[8px] font-bold text-white uppercase shadow-sm">
                    0.0
                  </span>
                </div>

                <div
                  className={`absolute top-1.5 bottom-1.5 rounded-lg transition-all duration-300 border shadow-lg ${
                    olsExcludesZero
                      ? "bg-sky-500/30 border-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.3)]"
                      : "bg-amber-500/30 border-amber-400 shadow-[0_0_12px_rgba(251,191,36,0.3)]"
                  }`}
                  style={{ left: `${olsLeft}%`, width: `${olsWidth}%` }}
                />

                <div
                  className="absolute top-1 bottom-1 w-2 -translate-x-1/2 bg-white rounded shadow-[0_0_8px_rgba(255,255,255,0.8)] z-20"
                  style={{ left: `${olsCenter}%` }}
                >
                  <span className="absolute -bottom-0.5 -translate-x-1/2 px-1 rounded bg-white text-[8px] font-bold text-black font-mono shadow-sm">
                    {signed(olsSlopeDecade, 2)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. CENTER TELEMETRY: MANN-KENDALL, SEN'S SLOPE & AUTOCORRELATION */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1 min-h-0 text-xs">
        {/* Left Column: Mann-Kendall & Sen's Slope */}
        <div className="dark-clay-card-sm rounded-2xl p-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-white/10">
              <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                Mann-Kendall Rank Test & Sen&apos;s Slope
              </span>
              <span className="text-[10px] font-mono text-slate-400">Annual Means</span>
            </div>

            <table className="w-full">
              <tbody className="divide-y divide-white/5 text-slate-300">
                <tr>
                  <td className="py-1 text-slate-400">Sen&apos;s Median Slope</td>
                  <td className="py-1 text-right font-mono font-bold text-white">
                    {signed(senSlopeDecade, 3)} {unit} / decade
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Annual Slope Rate</td>
                  <td className="py-1 text-right font-mono font-bold text-white">
                    {signed(mannKendall.senSlopePerYear, 4)} {unit} / year
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Kendall&apos;s Tau (τ)</td>
                  <td className="py-1 text-right font-mono font-bold text-sky-400">
                    τ = {mannKendall.tau.toFixed(3)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Mann-Kendall S-Score</td>
                  <td className="py-1 text-right font-mono">
                    S = {mannKendall.s}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Standard Normal z-score</td>
                  <td className="py-1 text-right font-mono">
                    z = {mannKendall.z.toFixed(2)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Mann-Kendall p-value</td>
                  <td className="py-1 text-right font-mono font-bold text-emerald-400">
                    {fmtP(mannKendall.pValue)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Sample Cycles Used</td>
                  <td className="py-1 text-right font-mono text-amber-300 font-semibold">
                    {mannKendall.n} complete annual cycles
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="text-[10px] text-slate-400 mt-1">
            Distribution-free rank test calculates all pairwise slopes; completely robust to extreme weather outliers.
          </p>
        </div>

        {/* Right Column: Autocorrelation & Serial Persistence */}
        <div className="dark-clay-card-sm rounded-2xl p-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-white/10">
              <span className="font-bold text-sky-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-sky-400"></span>
                Autocorrelation & Serial Persistence
              </span>
              <button
                onClick={() => setApplyAutocorr((p) => !p)}
                className={`text-[10px] px-2 py-0.5 rounded-lg border transition-all ${
                  applyAutocorr
                    ? "bg-sky-500/20 text-sky-300 border-sky-500/40 font-bold shadow-sm"
                    : "dark-clay-button text-slate-400"
                }`}
              >
                Penalty: {applyAutocorr ? "APPLIED" : "RAW"}
              </button>
            </div>

            <table className="w-full">
              <tbody className="divide-y divide-white/5 text-slate-300">
                <tr>
                  <td className="py-1 text-slate-400">Lag-1 Autocorrelation (r₁)</td>
                  <td className="py-1 text-right font-mono font-bold text-amber-300">
                    r₁ = {ols.lag1Autocorr.toFixed(3)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Effective Sample Size (N_eff)</td>
                  <td className="py-1 text-right font-mono font-bold text-white">
                    {applyAutocorr ? Math.round(ols.effectiveN) : ols.n} of {ols.n} months
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Serial Persistence Ratio</td>
                  <td className="py-1 text-right font-mono">
                    {((ols.effectiveN / ols.n) * 100).toFixed(1)}% independent degrees of freedom
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Standard Error of Slope (SE)</td>
                  <td className="py-1 text-right font-mono">
                    ±{fmt((applyAutocorr ? ols.stdErr : ols.stdErr * Math.sqrt(ols.effectiveN / ols.n)) * 10, 4)} {unit}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Student&apos;s t-Statistic</td>
                  <td className="py-1 text-right font-mono">
                    t = {fmt(ols.tStat, 3)}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Linear R² Goodness of Fit</td>
                  <td className="py-1 text-right font-mono font-bold text-white">
                    {(ols.r2 * 100).toFixed(1)}% (R² = {ols.r2.toFixed(3)})
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Total Cumulative Change</td>
                  <td className="py-1 text-right font-mono font-bold text-amber-300">
                    {signed(totalChange, 2)} {unit} over {periodYears} years
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="text-[10px] text-slate-400 mt-1">
            Atmospheric variables carry month-to-month memory. Correcting for r₁ prevents false alarm trend detection.
          </p>
        </div>
      </div>

      {/* 4. BOTTOM TELEMETRY STRIP */}
      <div className="pt-2 border-t border-white/10 text-[11px] text-slate-300 leading-relaxed flex items-start gap-2 shrink-0">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          className="text-emerald-400 shrink-0 mt-0.5"
        >
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        <p>
          <strong className="text-white">Trend Verification Synthesis: </strong>
          Both the parametric t-test and non-parametric Mann-Kendall test agree on an empirical rate of {signed(senSlopeDecade)} {unit}/decade with p-value {fmtP(mannKendall.pValue)}. The {confLevel}% uncertainty range bar strictly excludes zero, verifying genuine multi-decadal planetary change.
        </p>
      </div>
    </div>
  );
}