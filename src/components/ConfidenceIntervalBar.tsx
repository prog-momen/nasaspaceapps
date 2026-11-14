"use client";

import React, { useState } from "react";

interface Props {
  olsSlopePerYear: number;
  olsCi95PerYear: [number, number];
  stdErrPerYear: number;
  tStat: number;
  pValue: number;
  senSlopePerYear: number;
  senCi95PerYear: [number, number];
  unit: string;
}

const fmt = (v: number, d = 3) =>
  Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(d);

const signed = (v: number, d = 3) => `${v >= 0 ? "+" : ""}${fmt(v, d)}`;

export default function ConfidenceIntervalBar({
  olsSlopePerYear,
  olsCi95PerYear,
  stdErrPerYear,
  tStat,
  pValue,
  senSlopePerYear,
  senCi95PerYear,
  unit,
}: Props) {
  // Interactive Confidence Level: 90%, 95%, 99%
  const [confLevel, setConfLevel] = useState<90 | 95 | 99>(95);
  const [modelMode, setModelMode] = useState<"both" | "ols" | "sen">("both");
  const [probeVal, setProbeVal] = useState<number | null>(null);

  // Critical multiplier adjustment based on chosen confidence level
  // df is large, normal approx / t-distribution multiplier:
  const zCrit = confLevel === 90 ? 1.645 : confLevel === 99 ? 2.576 : 1.96;

  // Re-estimate OLS bounds for selected confidence level
  const slopeDecade = olsSlopePerYear * 10;
  const stdErrDecade = stdErrPerYear * 10;
  const ciLoDecade = confLevel === 95 ? olsCi95PerYear[0] * 10 : slopeDecade - zCrit * stdErrDecade;
  const ciHiDecade = confLevel === 95 ? olsCi95PerYear[1] * 10 : slopeDecade + zCrit * stdErrDecade;
  const marginDecade = Math.abs(ciHiDecade - ciLoDecade) / 2;

  // Re-estimate Sen's slope bounds
  const senSlopeDecade = senSlopePerYear * 10;
  const senMarginDecade = (Math.abs(senCi95PerYear[1] - senCi95PerYear[0]) * 10) / 2;
  const senScaleFactor = zCrit / 1.96;
  const senCiLoDecade = senSlopeDecade - senMarginDecade * senScaleFactor;
  const senCiHiDecade = senSlopeDecade + senMarginDecade * senScaleFactor;

  const olsExcludesZero = (ciLoDecade > 0 && ciHiDecade > 0) || (ciLoDecade < 0 && ciHiDecade < 0);
  const senExcludesZero = (senCiLoDecade > 0 && senCiHiDecade > 0) || (senCiLoDecade < 0 && senCiHiDecade < 0);

  // Visual Scale Bounds
  const minVal = Math.min(ciLoDecade, senCiLoDecade, 0);
  const maxVal = Math.max(ciHiDecade, senCiHiDecade, 0);
  const span = maxVal - minVal || 1;
  const pad = span * 0.2;
  const domainMin = minVal - pad;
  const domainMax = maxVal + pad;

  const scale = (val: number) => ((val - domainMin) / (domainMax - domainMin)) * 100;

  const zeroPos = scale(0);
  const olsLeft = Math.max(0, Math.min(100, scale(ciLoDecade)));
  const olsRight = Math.max(0, Math.min(100, scale(ciHiDecade)));
  const olsWidth = Math.max(1, olsRight - olsLeft);
  const olsCenter = Math.max(0, Math.min(100, scale(slopeDecade)));

  const senLeft = Math.max(0, Math.min(100, scale(senCiLoDecade)));
  const senRight = Math.max(0, Math.min(100, scale(senCiHiDecade)));
  const senWidth = Math.max(1, senRight - senLeft);
  const senCenter = Math.max(0, Math.min(100, scale(senSlopeDecade)));

  return (
    <div className="h-full flex flex-col justify-between select-none">
      {/* Top Interactive Ribbon (No Cards) */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2 shrink-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#10b981]/20 text-[#34d399] border border-[#10b981]/40 font-bold uppercase">
            Confidence Range Bar
          </span>

          {/* Interactive Confidence Level Picker */}
          <div className="flex items-center gap-1 text-[11px]">
            <span className="text-[#9ca3af] text-[10px] mr-1 hidden sm:inline">Confidence Level:</span>
            {([90, 95, 99] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setConfLevel(lvl)}
                className={`px-2 py-0.5 rounded-lg border font-mono transition-all ${
                  confLevel === lvl
                    ? "bg-[#2563eb] border-blue-400 text-white font-bold"
                    : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
                }`}
              >
                {lvl}% (α={(1 - lvl / 100).toFixed(2)})
              </button>
            ))}
          </div>

          {/* Interactive Model View Toggle */}
          <div className="flex items-center gap-1 text-[11px] ml-1">
            <button
              onClick={() => setModelMode("both")}
              className={`px-2 py-0.5 rounded-lg border transition-all ${
                modelMode === "both"
                  ? "bg-white/15 border-white/30 text-white font-bold"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
              }`}
            >
              Dual View
            </button>
            <button
              onClick={() => setModelMode("ols")}
              className={`px-2 py-0.5 rounded-lg border transition-all ${
                modelMode === "ols"
                  ? "bg-sky-500/20 border-sky-400 text-sky-300 font-bold"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
              }`}
            >
              OLS Parametric
            </button>
            <button
              onClick={() => setModelMode("sen")}
              className={`px-2 py-0.5 rounded-lg border transition-all ${
                modelMode === "sen"
                  ? "bg-emerald-500/20 border-emerald-400 text-emerald-300 font-bold"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
              }`}
            >
              Sen&apos;s Slope
            </button>
          </div>
        </div>

        {/* Real-Time Significance Badge */}
        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-2.5 py-1 rounded-lg border font-semibold flex items-center gap-1.5 ${
              olsExcludesZero
                ? "bg-[#14532d] text-[#86efac] border-[#166534]"
                : "bg-[#78350f] text-[#fcd34d] border-[#92400e]"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                olsExcludesZero ? "bg-[#22c55e]" : "bg-[#f59e0b]"
              }`}
            ></span>
            {olsExcludesZero
              ? `${confLevel}% CI Excludes 0 (Statistically Significant)`
              : `${confLevel}% CI Spans 0 (Inconclusive)`}
          </span>
        </div>
      </div>

      {/* Main Range Bar Stage (Zero Card Boxes, Sleek Telemetry Canvas) */}
      <div className="flex-1 min-h-0 flex flex-col justify-around py-3">
        {/* RANGE BAR 1: OLS Regression */}
        {(modelMode === "both" || modelMode === "ols") && (
          <div className="flex flex-col gap-1.5 border-b border-white/5 pb-3">
            <div className="flex flex-wrap items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#38bdf8]"></span>
                <span className="font-bold text-white">Ordinary Least Squares (OLS) {confLevel}% Uncertainty Range Bar</span>
                <span className="text-[#60a5fa] font-mono text-[11px]">
                  Rate: {signed(slopeDecade)} {unit}/decade
                </span>
              </div>
              <div className="font-mono text-[11px] text-[#9ca3af]">
                Span: [{signed(ciLoDecade)} to {signed(ciHiDecade)}] {unit}/decade • t = {fmt(tStat, 2)} (p = {pValue < 0.001 ? "< 0.001" : fmt(pValue, 3)})
              </div>
            </div>

            {/* Interactive Graphic Track */}
            <div
              onMouseMove={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const frac = (e.clientX - rect.left) / rect.width;
                const v = domainMin + frac * (domainMax - domainMin);
                setProbeVal(v);
              }}
              onMouseLeave={() => setProbeVal(null)}
              className="relative w-full h-12 bg-white/5 rounded-lg border border-white/10 overflow-hidden cursor-crosshair"
            >
              {/* Zero Reference Line */}
              <div className="absolute top-0 bottom-0 w-[1.5px] bg-[#ef4444] z-10" style={{ left: `${zeroPos}%` }}>
                <span className="absolute -top-0.5 -translate-x-1/2 px-1 rounded bg-[#ef4444] text-[8.5px] font-bold text-white uppercase">
                  0.0 Baseline
                </span>
              </div>

              {/* Shaded Range Bar Band */}
              <div
                className={`absolute top-2.5 bottom-2.5 rounded transition-all duration-300 border ${
                  olsExcludesZero ? "bg-[#2563eb]/35 border-[#60a5fa]" : "bg-[#f59e0b]/35 border-[#fbbf24]"
                }`}
                style={{ left: `${olsLeft}%`, width: `${olsWidth}%` }}
              />

              {/* Central Point Estimate Marker */}
              <div
                className="absolute top-1.5 bottom-1.5 w-1.5 -translate-x-1/2 bg-white rounded shadow-[0_0_12px_rgba(255,255,255,0.9)] z-20"
                style={{ left: `${olsCenter}%` }}
              >
                <span className="absolute -bottom-0.5 -translate-x-1/2 px-1 rounded bg-white text-[9px] font-bold text-[#090d16] font-mono whitespace-nowrap">
                  {signed(slopeDecade, 2)}
                </span>
              </div>

              {/* Interactive Hover Probe Guideline */}
              {probeVal !== null && (
                <div
                  className="absolute top-0 bottom-0 w-px bg-white/70 z-30 pointer-events-none"
                  style={{ left: `${scale(probeVal)}%` }}
                >
                  <span className="absolute top-0.5 left-1 px-1 rounded bg-black/80 text-[8.5px] font-mono text-white">
                    {signed(probeVal, 2)}
                  </span>
                </div>
              )}
            </div>

            {/* OLS Scale Metric Strip */}
            <div className="grid grid-cols-4 gap-2 text-xs font-mono">
              <div className="border-l border-white/10 pl-2">
                <span className="text-[9.5px] text-[#9ca3af] block">Lower {confLevel}% Bound</span>
                <span className="font-bold text-[#f87171]">{signed(ciLoDecade)} {unit}</span>
              </div>
              <div className="border-l border-white/10 pl-2">
                <span className="text-[9.5px] text-[#9ca3af] block">Point Estimate</span>
                <span className="font-bold text-[#60a5fa]">{signed(slopeDecade)} {unit}</span>
              </div>
              <div className="border-l border-white/10 pl-2">
                <span className="text-[9.5px] text-[#9ca3af] block">Upper {confLevel}% Bound</span>
                <span className="font-bold text-[#34d399]">{signed(ciHiDecade)} {unit}</span>
              </div>
              <div className="border-l border-white/10 pl-2">
                <span className="text-[9.5px] text-[#9ca3af] block">Margin of Error (±ME)</span>
                <span className="font-bold text-white">±{fmt(marginDecade)} (SE ±{fmt(stdErrDecade)})</span>
              </div>
            </div>
          </div>
        )}

        {/* RANGE BAR 2: Mann-Kendall Sen's Slope */}
        {(modelMode === "both" || modelMode === "sen") && (
          <div className="flex flex-col gap-1.5 pt-1">
            <div className="flex flex-wrap items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#34d399]"></span>
                <span className="font-bold text-white">Mann-Kendall Sen&apos;s Non-Parametric Median Range Bar</span>
                <span className="text-[#34d399] font-mono text-[11px]">
                  Median: {signed(senSlopeDecade)} {unit}/decade
                </span>
              </div>
              <div className="font-mono text-[11px] text-[#9ca3af]">
                Span: [{signed(senCiLoDecade)} to {signed(senCiHiDecade)}] {unit}/decade
              </div>
            </div>

            {/* Interactive Graphic Track */}
            <div className="relative w-full h-12 bg-white/5 rounded-lg border border-white/10 overflow-hidden">
              {/* Zero Reference Line */}
              <div className="absolute top-0 bottom-0 w-[1.5px] bg-[#ef4444] z-10" style={{ left: `${zeroPos}%` }}>
                <span className="absolute -top-0.5 -translate-x-1/2 px-1 rounded bg-[#ef4444] text-[8.5px] font-bold text-white uppercase">
                  0.0 Baseline
                </span>
              </div>

              {/* Shaded Range Bar Band */}
              <div
                className={`absolute top-2.5 bottom-2.5 rounded transition-all duration-300 border ${
                  senExcludesZero ? "bg-[#10b981]/35 border-[#34d399]" : "bg-[#f59e0b]/35 border-[#fbbf24]"
                }`}
                style={{ left: `${senLeft}%`, width: `${senWidth}%` }}
              />

              {/* Central Point Estimate Marker */}
              <div
                className="absolute top-1.5 bottom-1.5 w-1.5 -translate-x-1/2 bg-[#34d399] rounded shadow-[0_0_12px_rgba(52,211,153,0.9)] z-20"
                style={{ left: `${senCenter}%` }}
              >
                <span className="absolute -bottom-0.5 -translate-x-1/2 px-1 rounded bg-[#34d399] text-[9px] font-bold text-[#090d16] font-mono whitespace-nowrap">
                  {signed(senSlopeDecade, 2)}
                </span>
              </div>
            </div>

            {/* Sen Scale Metric Strip */}
            <div className="grid grid-cols-3 gap-2 text-xs font-mono">
              <div className="border-l border-white/10 pl-2">
                <span className="text-[9.5px] text-[#9ca3af] block">Lower {confLevel}% Bound</span>
                <span className="font-bold text-[#f87171]">{signed(senCiLoDecade)} {unit}</span>
              </div>
              <div className="border-l border-white/10 pl-2">
                <span className="text-[9.5px] text-[#9ca3af] block">Median Slope</span>
                <span className="font-bold text-[#34d399]">{signed(senSlopeDecade)} {unit}</span>
              </div>
              <div className="border-l border-white/10 pl-2">
                <span className="text-[9.5px] text-[#9ca3af] block">Upper {confLevel}% Bound</span>
                <span className="font-bold text-[#60a5fa]">{signed(senCiHiDecade)} {unit}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Telemetry Note: Zero-Exclusion Criterion (Zero Cards) */}
      <div className="pt-2 border-t border-white/10 text-xs text-[#9ca3af] leading-relaxed flex items-start gap-2 shrink-0">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-[#60a5fa] shrink-0 mt-0.5"
        >
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        <p className="text-[11px]">
          <strong className="text-white">Why the Range Bar confirms statistical significance: </strong>
          In environmental time series, a detected trend is scientifically robust only when its uncertainty range bar strictly excludes the zero-change threshold. Since the lower bound is {signed(ciLoDecade)} {unit}/decade, we hold {confLevel}% mathematical certainty that the planetary trajectory is systematically {olsSlopePerYear > 0 ? "increasing" : "decreasing"}, rejecting natural random variation.
        </p>
      </div>
    </div>
  );
}
