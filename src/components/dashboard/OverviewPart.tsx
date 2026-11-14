"use client";

import React, { useState } from "react";
import { fmt } from "../PageFrame";

interface Props {
  series: { date: string; value: number }[];
  trend: {
    mean: number;
    stdDev: number;
    min: { date: string; value: number };
    max: { date: string; value: number };
    period: { start: string; end: string; years: number; months: number };
  };
  unit: string;
  variableName: string;
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

export default function OverviewPart({ series, trend, unit, variableName }: Props) {
  const [activeQuantilePercent, setActiveQuantilePercent] = useState<number>(50);
  const [showChartGuide, setShowChartGuide] = useState<boolean>(false);

  const values = series.map((s) => s.value);
  const sorted = [...values].sort((a, b) => a - b);
  const n = values.length;

  const variance = trend.stdDev * trend.stdDev;
  const rangeVal = trend.max.value - trend.min.value;

  const p10 = quantile(sorted, 0.10);
  const p25 = quantile(sorted, 0.25);
  const p50 = quantile(sorted, 0.50); // Median
  const p75 = quantile(sorted, 0.75);
  const p90 = quantile(sorted, 0.90);
  const iqr = p75 - p25;

  const probedQuantileVal = quantile(sorted, activeQuantilePercent / 100);

  // Build histogram bins (7 rounded pill bars like Listening Overview in the reference design)
  const numBins = 7;
  const binWidth = (rangeVal || 1) / numBins;
  const bins = Array.from({ length: numBins }, (_, i) => {
    const lo = trend.min.value + i * binWidth;
    const hi = lo + binWidth;
    const count = values.filter((v) => (i === numBins - 1 ? v >= lo && v <= hi : v >= lo && v < hi)).length;
    return { lo, hi, mid: (lo + hi) / 2, count, pct: (count / n) * 100 };
  });
  const maxBinCount = Math.max(...bins.map((b) => b.count)) || 1;

  // Luminous dark gradients matching the dark neumorphic pill capsules
  const barGradients = [
    "from-[#0284c7] to-[#38bdf8]",
    "from-[#059669] to-[#34d399]",
    "from-[#0284c7] to-[#0ea5e9]",
    "from-[#0d9488] to-[#2dd4bf]",
    "from-[#2563eb] to-[#60a5fa]",
    "from-[#4f46e5] to-[#818cf8]",
    "from-[#7c3aed] to-[#c084fc]",
  ];

  return (
    <div className="h-full flex flex-col justify-between gap-2.5 select-none text-slate-100 font-sans">
      {/* 1. TOP 4 METRIC STAT CARDS (Dark Neumorphic Clay Badges) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-3 shrink-0">
        {/* CARD 1: MEAN (Dark Emerald Clay) */}
        <div className="dark-clay-badge-mint rounded-2xl sm:rounded-3xl p-3 sm:p-3.5 flex flex-col justify-between transition-transform hover:-translate-y-0.5">
          <div className="flex items-center justify-between">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-[#34d399]">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14"></path>
                <path d="M4 12h16"></path>
                <path d="M9 19V5"></path>
              </svg>
            </div>
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-[#34d399] border border-emerald-500/30">
              N={n} mo
            </span>
          </div>
          <div className="mt-2">
            <span className="text-[11px] font-semibold text-emerald-300 block">Arithmetic Mean (μ)</span>
            <div className="text-xl sm:text-2xl font-black text-white tracking-tight font-mono mt-0.5">
              {fmt(trend.mean, 2)} <span className="text-xs font-semibold text-emerald-400">{unit}</span>
            </div>
            <span className="text-[10px] text-emerald-400/80 font-medium mt-0.5 block truncate">
              Variance σ²: {fmt(variance, 2)} {unit}²
            </span>
          </div>
        </div>

        {/* CARD 2: MEDIAN (Dark Ocean Sky Clay) */}
        <div className="dark-clay-badge-sky rounded-2xl sm:rounded-3xl p-3 sm:p-3.5 flex flex-col justify-between transition-transform hover:-translate-y-0.5">
          <div className="flex items-center justify-between">
            <div className="w-8 h-8 rounded-xl bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-[#38bdf8]">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
              </svg>
            </div>
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-sky-500/20 text-[#38bdf8] border border-sky-500/30">
              50th %
            </span>
          </div>
          <div className="mt-2">
            <span className="text-[11px] font-semibold text-sky-300 block">Median (Q2 / p50)</span>
            <div className="text-xl sm:text-2xl font-black text-white tracking-tight font-mono mt-0.5">
              {fmt(p50, 2)} <span className="text-xs font-semibold text-sky-400">{unit}</span>
            </div>
            <span className="text-[10px] text-sky-400/80 font-medium mt-0.5 block truncate">
              IQR Spread: {fmt(iqr, 2)} {unit}
            </span>
          </div>
        </div>

        {/* CARD 3: MIN / MAX RANGE (Dark Amber Clay) */}
        <div className="dark-clay-badge-frost rounded-2xl sm:rounded-3xl p-3 sm:p-3.5 flex flex-col justify-between transition-transform hover:-translate-y-0.5">
          <div className="flex items-center justify-between">
            <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-[#fbbf24]">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
            </div>
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-amber-500/20 text-[#fbbf24] border border-amber-500/30">
              Extremes
            </span>
          </div>
          <div className="mt-2">
            <span className="text-[11px] font-semibold text-amber-300 block">Min / Max Range</span>
            <div className="text-lg sm:text-xl font-black text-white tracking-tight font-mono mt-0.5 truncate">
              {fmt(trend.min.value, 1)} – {fmt(trend.max.value, 1)} <span className="text-xs font-semibold text-amber-400">{unit}</span>
            </div>
            <span className="text-[10px] text-amber-400/80 font-medium mt-0.5 block truncate">
              Dynamic Span: {fmt(rangeVal, 2)} {unit}
            </span>
          </div>
        </div>

        {/* CARD 4: STANDARD DEVIATION (Dark Periwinkle Clay) */}
        <div className="dark-clay-badge-periwinkle rounded-2xl sm:rounded-3xl p-3 sm:p-3.5 flex flex-col justify-between transition-transform hover:-translate-y-0.5">
          <div className="flex items-center justify-between">
            <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-[#c084fc]">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path>
              </svg>
            </div>
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-purple-500/20 text-[#c084fc] border border-purple-500/30">
              Dispersion
            </span>
          </div>
          <div className="mt-2">
            <span className="text-[11px] font-semibold text-purple-300 block">Std Deviation (σ)</span>
            <div className="text-xl sm:text-2xl font-black text-white tracking-tight font-mono mt-0.5">
              ±{fmt(trend.stdDev, 2)} <span className="text-xs font-semibold text-purple-400">{unit}</span>
            </div>
            <span className="text-[10px] text-purple-400/80 font-medium mt-0.5 block truncate">
              CV: {((trend.stdDev / (Math.abs(trend.mean) || 1)) * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* 2. CENTER SECTION: TWO 3D DARK CLAY CARDS WITH DETAILED CHART EXPLANATIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 flex-1 min-h-0">
        {/* LEFT CARD: Observational Frequency Distribution & Info about the Chart */}
        <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs sm:text-sm font-bold text-white">
                  Observational Frequency Distribution
                </h3>
                <span className="text-[9.5px] px-2 py-0.2 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30 font-mono">
                  {variableName}
                </span>
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">
                Distribution of {n} continuous monthly satellite records grouped into 7 range capsules
              </p>
            </div>

            <button
              onClick={() => setShowChartGuide((p) => !p)}
              className="text-[10px] font-bold text-sky-400 hover:text-sky-300 px-2 py-1 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all flex items-center gap-1"
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>{showChartGuide ? "Hide Guide" : "About Chart"}</span>
            </button>
          </div>

          {/* Expandable Chart Explanation or Vertical 3D Capsule Pill Bars */}
          {showChartGuide ? (
            <div className="dark-clay-inset rounded-2xl p-3 my-2 text-xs space-y-2 flex-1 overflow-y-auto">
              <div className="border-b border-white/10 pb-1.5">
                <strong className="text-sky-400 text-xs block">What this chart represents:</strong>
                <p className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
                  This histogram partitions the entire historical time series of {n} months into 7 equal value intervals (bins). The height of each 3D capsule represents the count and percentage of months that fell into that range.
                </p>
              </div>
              <div className="border-b border-white/10 pb-1.5">
                <strong className="text-emerald-400 text-xs block">What the chart reveals:</strong>
                <p className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
                  • <strong>Central Mode:</strong> The tallest capsule indicates the most common monthly climatological state ({fmt(bins[Math.floor(numBins / 2)].mid, 1)} {unit}).<br />
                  • <strong>Skewness:</strong> Asymmetry between the left (cold/dry) and right (warm/wet) tails identifies directional environmental pressure.<br />
                  • <strong>Outliers:</strong> Short outer capsules mark rare anomalous climate shocks.
                </p>
              </div>
              <div>
                <strong className="text-amber-400 text-xs block">Mathematical Bounds:</strong>
                <p className="text-[11px] text-slate-300 mt-0.5 font-mono">
                  Bin Width = (Max - Min) / 7 = {fmt(binWidth, 2)} {unit} per capsule.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 min-h-[140px] flex items-end justify-between gap-2 sm:gap-3 py-3 px-2">
              {bins.map((b, idx) => {
                const heightPct = Math.max(12, (b.count / maxBinCount) * 100);
                const grad = barGradients[idx % barGradients.length];
                return (
                  <div
                    key={idx}
                    className="flex-1 h-full flex flex-col justify-end items-center group relative cursor-pointer"
                  >
                    {/* Tooltip on hover */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-8 px-2 py-0.5 rounded-lg bg-slate-900 border border-white/20 text-white text-[9px] font-mono pointer-events-none whitespace-nowrap shadow-xl z-30">
                      {fmt(b.lo, 1)}–{fmt(b.hi, 1)} {unit}: {b.count} mo ({b.pct.toFixed(0)}%)
                    </div>

                    {/* 3D Pill Capsule Bar with luminous glow */}
                    <div
                      className={`w-6 sm:w-8 rounded-full bg-gradient-to-t ${grad} shadow-[0_4px_12px_rgba(0,0,0,0.6)] border border-white/20 group-hover:brightness-125 transition-all`}
                      style={{ height: `${heightPct}%` }}
                    />
                    <span className="text-[9px] font-mono font-semibold text-slate-400 mt-2 truncate">
                      {fmt(b.mid, 0)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Bottom Info About the Histogram */}
          <div className="flex items-center justify-between pt-2 border-t border-white/10 text-[10.5px] text-slate-400 font-mono">
            <span>Historical Minimum: <strong className="text-amber-400">{fmt(trend.min.value, 1)} {unit}</strong> ({trend.min.date})</span>
            <span>Historical Maximum: <strong className="text-amber-400">{fmt(trend.max.value, 1)} {unit}</strong> ({trend.max.date})</span>
          </div>
        </div>

        {/* RIGHT CARD: Percentiles & Interactive Quantile Probe with Chart Info */}
        <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs sm:text-sm font-bold text-white">
                  Percentiles Spectrum & Quantile Probe
                </h3>
                <span className="text-[9.5px] px-2 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono">
                  Quantiles
                </span>
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">
                Non-parametric ranking of monthly observations from p10 to p90
              </p>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
              IQR: {fmt(iqr, 2)} {unit}
            </span>
          </div>

          {/* 5 Percentile Pill Badges */}
          <div className="grid grid-cols-5 gap-1.5 py-2">
            {[
              { label: "P10", val: p10, desc: "Cold/Dry 10%" },
              { label: "P25", val: p25, desc: "Lower Quartile" },
              { label: "P50", val: p50, desc: "Median Midpoint" },
              { label: "P75", val: p75, desc: "Upper Quartile" },
              { label: "P90", val: p90, desc: "Warm/Wet 10%" },
            ].map((p, idx) => (
              <div
                key={idx}
                className="dark-clay-inset rounded-xl p-2 text-center flex flex-col justify-between"
              >
                <span className="text-[9.5px] font-bold text-sky-400 block">{p.label}</span>
                <span className="text-xs font-mono font-black text-white my-0.5 block">
                  {fmt(p.val, 1)}
                </span>
                <span className="text-[8px] text-slate-400 truncate block">{p.desc}</span>
              </div>
            ))}
          </div>

          {/* Interactive Sunken Debossed Quantile Probe Slider */}
          <div className="dark-clay-inset rounded-2xl p-2.5 sm:p-3 my-1">
            <div className="flex items-center justify-between text-xs font-mono mb-1.5">
              <span className="text-slate-300 font-bold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#38bdf8]"></span>
                Interactive Quantile Probe (p{activeQuantilePercent})
              </span>
              <span className="font-bold text-[#38bdf8] bg-sky-950 px-2 py-0.5 rounded-full border border-sky-500/40">
                {fmt(probedQuantileVal, 2)} {unit}
              </span>
            </div>

            <input
              type="range"
              min="1"
              max="99"
              value={activeQuantilePercent}
              onChange={(e) => setActiveQuantilePercent(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-full appearance-none cursor-pointer accent-[#38bdf8]"
            />

            <div className="flex justify-between text-[8.5px] font-mono text-slate-400 mt-1">
              <span>p1: {fmt(trend.min.value, 1)} (Min)</span>
              <span>p50: {fmt(p50, 1)} (Median)</span>
              <span>p99: {fmt(trend.max.value, 1)} (Max)</span>
            </div>
          </div>

          {/* Info About the Quantiles & Interquartile Range */}
          <div className="pt-2 border-t border-white/10 text-[10.5px] text-slate-300 flex items-center gap-2">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-sky-400 shrink-0">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <p className="leading-tight">
              <strong>Info about the IQR: </strong>
              The middle 50% of monthly records fall between <strong className="text-white">{fmt(p25, 1)}</strong> and <strong className="text-white">{fmt(p75, 1)} {unit}</strong>. Observations beyond p90 or below p10 represent acute multi-year anomalies.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}