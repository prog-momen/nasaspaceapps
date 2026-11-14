"use client";

import React, { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAsync } from "../lib/useAsync";
import PageFrame, { ErrorBox, Loading } from "./PageFrame";
import AnalysisControls from "./AnalysisControls";
import { LineChart, LineSeries, dateToX } from "./charts/Charts";
import AiAssistantTemplate from "./AiAssistantTemplate";
import {
  fetchAnalysis,
  parseSelection,
  selectionToParams,
  type Selection,
  type AnalysisResult,
} from "../lib/api-client";
import { COUNTRIES, Country } from "../data/countries";

const QUICK_VARIABLES = [
  { key: "T2M", label: "Air Temp", unit: "°C" },
  { key: "T2M_MAX", label: "Max Temp", unit: "°C" },
  { key: "PRECTOTCORR", label: "Precipitation", unit: "mm/day" },
  { key: "GWETROOT", label: "Soil Wetness", unit: "0-1" },
  { key: "TS", label: "Surface Temp", unit: "°C" },
];

const TIME_RANGES = [
  { key: "5Y", label: "5Y", years: 5 },
  { key: "10Y", label: "10Y", years: 10 },
  { key: "20Y", label: "20Y", years: 20 },
  { key: "All", label: "All", years: 999 },
] as const;

function fmt(v: number, digits = 2): string {
  return Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(digits);
}

function signed(v: number, digits = 2): string {
  return `${v >= 0 ? "+" : ""}${fmt(v, digits)}`;
}

function fmtP(p: number): string {
  if (p < 0.001) return "< 0.001";
  if (p < 0.01) return "< 0.01";
  return `= ${p.toFixed(3)}`;
}

/**
 * Lightweight interactive tooltip popover for technical details.
 */
function InfoTooltip({
  title,
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label="View technical details"
        className="w-4 h-4 rounded-full bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white text-[10px] font-mono flex items-center justify-center transition-colors cursor-help ml-1.5"
      >
        i
      </button>

      {open && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 rounded-xl bg-[#09101b] border border-white/20 text-xs text-slate-200 shadow-2xl backdrop-blur-md pointer-events-none transition-all duration-200">
          {title && <span className="text-sky-400 font-bold block text-[11px] mb-1">{title}</span>}
          <div className="text-[10px] leading-relaxed text-slate-300">{children}</div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-[#09101b]" />
        </div>
      )}
    </div>
  );
}

function DashboardContent({ data, sel }: { data: AnalysisResult; sel: Selection }) {
  const router = useRouter();
  const [timeRange, setTimeRange] = useState<"5Y" | "10Y" | "20Y" | "All">("All");
  const [showMovingAvg, setShowMovingAvg] = useState(false);
  const [showHotspots, setShowHotspots] = useState(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [editing, setEditing] = useState(false);

  const { trend: t, variable: v, region, series } = data;

  // Filter series according to selected time range
  const filteredSeries = useMemo(() => {
    if (timeRange === "All" || !series.length) return series;
    const endYear = Number(series[series.length - 1].date.slice(0, 4));
    const rangeObj = TIME_RANGES.find((r) => r.key === timeRange);
    const startYear = endYear - (rangeObj?.years ?? 10);
    return series.filter((s) => Number(s.date.slice(0, 4)) >= startYear);
  }, [series, timeRange]);

  // Decadal & annual slope
  const slopeDecade = t.ols.slopePerYear * 10;
  const isSignificant = t.verdict === "significant";
  const isWarmingOrIncrease = t.ols.slopePerYear > 0;

  // 1-Year Forecast & uncertainty band calculation (12 future months)
  const lastPoint = series[series.length - 1];
  const lastDate = lastPoint?.date ?? `${t.period.end}-12`;
  const lastYear = Number(lastDate.slice(0, 4));
  const lastMonth = Number(lastDate.slice(5, 7));
  const forecastStartX = dateToX(lastDate);

  const climMean = t.seasonalClimatology.reduce((a, b) => a + b, 0) / 12;
  const forecastMargin = Math.max(0.2, 1.96 * (t.stdDev * 0.35 + Math.abs(t.ols.stdErr)));

  const future12Months = useMemo(() => {
    const pts: { x: number; y: number; lower: number; upper: number }[] = [];
    for (let m = 1; m <= 12; m++) {
      const monthIdx = (lastMonth + m - 1) % 12;
      const seasonalShift = t.seasonalClimatology[monthIdx] - climMean;
      const futureDecimalYear = lastYear + (lastMonth + m - 0.5) / 12;
      const futureTrend = lastPoint.trend + t.ols.slopePerYear * (m / 12);
      const predictedVal = futureTrend + seasonalShift;
      const uncertaintyExpansion = forecastMargin * (1 + 0.04 * m);

      pts.push({
        x: futureDecimalYear,
        y: predictedVal,
        lower: predictedVal - uncertaintyExpansion,
        upper: predictedVal + uncertaintyExpansion,
      });
    }
    return pts;
  }, [lastPoint, lastMonth, lastYear, t.seasonalClimatology, climMean, t.ols.slopePerYear, forecastMargin]);

  const projectedNextYearMean =
    future12Months.reduce((sum, p) => sum + p.y, 0) / future12Months.length;

  // Moving average series (for optional secondary overlay)
  const movingAvgPoints = useMemo(() => {
    if (!showMovingAvg) return [];
    const pts = filteredSeries.map((s) => ({ x: dateToX(s.date), y: s.value }));
    const out: { x: number; y: number }[] = [];
    for (let i = 0; i < pts.length; i++) {
      const start = Math.max(0, i - 11);
      const slice = pts.slice(start, i + 1);
      const avg = slice.reduce((acc, p) => acc + p.y, 0) / slice.length;
      out.push({ x: pts[i].x, y: avg });
    }
    return out;
  }, [filteredSeries, showMovingAvg]);

  // Construct chart series
  const chartSeries: LineSeries[] = useMemo(() => {
    const list: LineSeries[] = [
      {
        name: "Historical Observed",
        color: "#38bdf8",
        points: filteredSeries.map((s) => ({ x: dateToX(s.date), y: s.value })),
        width: 1.8,
      },
      {
        name: "Linear Trend Line",
        color: "#f59e0b",
        points: filteredSeries.map((s) => ({ x: dateToX(s.date), y: s.trend })),
        dashed: true,
        width: 2.2,
      },
      {
        name: "1-Year Forecast",
        color: "#38bdf8",
        points: [
          { x: dateToX(lastPoint.date), y: lastPoint.value },
          ...future12Months.map((p) => ({ x: p.x, y: p.y })),
        ],
        dashed: true,
        width: 2,
      },
    ];

    if (showMovingAvg && movingAvgPoints.length) {
      list.push({
        name: "12M Rolling Average",
        color: "#34d399",
        points: movingAvgPoints,
        width: 2,
      });
    }

    return list;
  }, [filteredSeries, lastPoint, future12Months, showMovingAvg, movingAvgPoints]);

  const forecastBand = useMemo(() => {
    return {
      color: "#38bdf8",
      points: [
        {
          x: dateToX(lastPoint.date),
          lo: lastPoint.value - forecastMargin,
          hi: lastPoint.value + forecastMargin,
        },
        ...future12Months.map((p) => ({ x: p.x, lo: p.lower, hi: p.upper })),
      ],
    };
  }, [lastPoint, future12Months, forecastMargin]);

  // Country object for RAG Assistant integration
  const countryObj: Country = useMemo(() => {
    const match = COUNTRIES.find((c) => c.name.toLowerCase() === region.name.toLowerCase());
    if (match) return match;
    const base = COUNTRIES[0];
    return {
      id: region.name.toLowerCase().replace(/[^a-z0-9]/g, "-") || "glo",
      name: region.name,
      officialName: region.name,
      code2: (region.country_code ?? "GL").slice(0, 2).toUpperCase(),
      code3: region.country_code ?? "GLO",
      region: "Americas",
      subregion: "Global Study Site",
      capital: region.name,
      lat: region.lat,
      lng: region.lon,
      zoom: base ? base.zoom : 2.0,
      population: "N/A",
      area: "N/A",
      currency: "N/A",
      timezone: "UTC",
    };
  }, [region]);

  return (
    <PageFrame
      title={`NASA Trend Detective: ${region.name}`}
      subtitle={`${v.name} (${v.unit}) • ${t.period.start}–${t.period.end}`}
      noScroll={false}
      maxWidth="max-w-6xl"
      theme="clay"
      hideHeader={true}
    >
      <div className="w-full flex flex-col gap-4 py-2 px-2 sm:px-4 text-slate-100 font-sans select-none">
        {/* ================= 1. CONTEXT HEADER (Stagger 1) ================= */}
        <section className="stagger-1 dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col gap-3 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
            {/* Region Title + Coordinates + Variable Switcher */}
            <div className="flex flex-col min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
                  Earth System Trend Detective
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {region.lat > 0 ? `${region.lat.toFixed(1)}°N` : `${Math.abs(region.lat).toFixed(1)}°S`},{" "}
                  {region.lon > 0 ? `${region.lon.toFixed(1)}°E` : `${Math.abs(region.lon).toFixed(1)}°W`}
                </span>
              </div>

              <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight mt-1 flex items-center gap-2">
                <span>{region.name}</span>
                <span className="text-sm font-normal text-slate-400">/ {v.name}</span>
              </h1>
            </div>

            {/* Top Action Pills: Quick Variables + 3D Globe Link */}
            <div className="flex flex-wrap items-center gap-1.5">
              {QUICK_VARIABLES.map((qv) => {
                const isSel = v.key === qv.key;
                return (
                  <button
                    key={qv.key}
                    onClick={() => {
                      if (!isSel) {
                        router.replace(`/dashboard?${selectionToParams({ ...sel, variable: qv.key })}`);
                      }
                    }}
                    className={`px-2.5 py-1 rounded-xl text-xs font-semibold transition-all border ${
                      isSel
                        ? "bg-sky-500 text-white border-sky-400 shadow-md shadow-sky-900/40"
                        : "dark-clay-button text-slate-300 hover:text-white"
                    }`}
                  >
                    {qv.label}
                  </button>
                );
              })}

              <Link
                href={`/?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(region.name)}`}
                className="dark-clay-button px-3 py-1 rounded-xl text-xs font-bold text-sky-300 hover:text-white flex items-center gap-1.5 transition-all ml-1 border border-sky-500/30"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="2" y1="12" x2="22" y2="12"></line>
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                </svg>
                <span>3D Globe</span>
              </Link>
            </div>
          </div>

          {/* 1-Line Plain-Language Definition + Time-Range Switch (5Y / 10Y / 20Y / All) */}
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <p className="text-slate-300 text-xs sm:text-sm font-medium leading-relaxed flex-1 min-w-[260px]">
              {v.definition || `Observing monthly ${v.name.toLowerCase()} anomalies across a continuous 40+ year satellite record.`}
            </p>

            {/* Time-Range Switcher */}
            <div className="flex items-center gap-1 dark-clay-inset p-1 rounded-xl">
              <span className="text-[10px] text-slate-400 font-mono px-1.5 font-bold uppercase">Time Range:</span>
              {TIME_RANGES.map((r) => {
                const isActive = timeRange === r.key;
                return (
                  <button
                    key={r.key}
                    onClick={() => setTimeRange(r.key)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold font-mono transition-all ${
                      isActive
                        ? "bg-sky-500 text-white shadow-md shadow-sky-900/50"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {r.label}
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        {/* Region Custom Period Drawer if open */}
        {editing && (
          <div className="dark-clay-card rounded-2xl p-3 shadow-2xl">
            <AnalysisControls
              lat={sel.lat}
              lon={sel.lon}
              name={sel.name}
              initial={sel}
              submitLabel="Apply Custom Period"
              onApply={(s) => {
                setEditing(false);
                router.replace(`/dashboard?${selectionToParams(s)}`);
              }}
            />
          </div>
        )}

        {/* ================= 2. VERDICT KPI STRIP (Max 3 Cards) (Stagger 2) ================= */}
        <section className="stagger-2 grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* CARD 1: RATE OF CHANGE & DIRECTION */}
          <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-3.5 sm:p-4 flex flex-col justify-between transition-transform hover:-translate-y-0.5 shadow-lg border border-white/10">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                1. Rate of Change
              </span>
              <InfoTooltip title="Rate of Change & Sen's Slope">
                <p>
                  • <strong>Sen&apos;s Slope:</strong> {signed(t.mannKendall.senSlopePerYear * 10, 3)} {v.unit}/decade (median slope of all pairwise sample points, robust to weather extremes).<br />
                  • <strong>Linear OLS:</strong> {signed(slopeDecade, 3)} {v.unit}/decade.<br />
                  • <strong>Formula:</strong> Total Δ = Slope × {t.period.years} years.
                </p>
              </InfoTooltip>
            </div>

            <div className="my-2">
              <div className="flex items-baseline gap-2">
                <span
                  className={`text-2xl sm:text-3xl font-black font-mono tracking-tight ${
                    isWarmingOrIncrease ? "text-amber-400" : "text-sky-400"
                  }`}
                >
                  {signed(slopeDecade, 2)}
                </span>
                <span className="text-xs font-bold text-slate-300 font-mono">
                  {v.unit} / decade
                </span>
              </div>

              <div className="flex items-center gap-1.5 mt-1 text-xs">
                <span
                  className={`inline-flex items-center gap-1 font-bold ${
                    isWarmingOrIncrease ? "text-amber-400" : "text-sky-400"
                  }`}
                >
                  {isWarmingOrIncrease ? "▲ Upward Trend" : "▼ Downward Trend"}
                </span>
                <span className="text-slate-400 text-[11px]">
                  ({signed(t.totalChange, 1)} {v.unit} over {t.period.years}y)
                </span>
              </div>
            </div>

            <span className="text-[10px] text-slate-400 font-medium">
              Rate answers: <em>How much is it changing?</em>
            </span>
          </div>

          {/* CARD 2: SIGNIFICANCE BADGE */}
          <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-3.5 sm:p-4 flex flex-col justify-between transition-transform hover:-translate-y-0.5 shadow-lg border border-white/10">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                2. Statistical Significance
              </span>
              <InfoTooltip title="Mann-Kendall Rank Significance">
                <p>
                  • <strong>p-value:</strong> {fmtP(t.mannKendall.pValue)} (threshold: p &lt; 0.05).<br />
                  • <strong>Kendall&apos;s Tau (τ):</strong> {t.mannKendall.tau.toFixed(3)}.<br />
                  • <strong>Standard Normal Score (z):</strong> {t.mannKendall.z.toFixed(2)}.<br />
                  • Confirms whether drift exceeds random climate noise.
                </p>
              </InfoTooltip>
            </div>

            <div className="my-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs sm:text-sm font-bold border shadow-sm">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isSignificant ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : "bg-amber-400"
                  }`}
                />
                <span className={isSignificant ? "text-emerald-300" : "text-amber-300"}>
                  {isSignificant ? "Statistically Significant" : "Not Significant Yet"}
                </span>
              </div>

              <p className="text-xs text-slate-300 mt-2 font-medium">
                {isSignificant
                  ? "Confidence > 95%: Trend strictly exceeds multi-year natural weather noise."
                  : "Observed variations remain within historical natural climatological noise."}
              </p>
            </div>

            <span className="text-[10px] text-slate-400 font-medium">
              Badge answers: <em>Is it statistically significant?</em>
            </span>
          </div>

          {/* CARD 3: 1-YEAR RISK / TREND OUTLOOK */}
          <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-3.5 sm:p-4 flex flex-col justify-between transition-transform hover:-translate-y-0.5 shadow-lg border border-white/10">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                3. 1-Year Trend Outlook
              </span>
              <InfoTooltip title="1-Year Forecast & Uncertainty Envelope">
                <p>
                  • <strong>Projected Mean:</strong> {fmt(projectedNextYearMean, 2)} {v.unit}.<br />
                  • <strong>95% Uncertainty Margin:</strong> ±{fmt(forecastMargin, 2)} {v.unit}.<br />
                  • <strong>Serial Persistence (r₁):</strong> {t.ols.lag1Autocorr.toFixed(2)} with {Math.round(t.ols.effectiveN)} independent months.<br />
                  • Incorporates secular drift + seasonal harmonic climatology.
                </p>
              </InfoTooltip>
            </div>

            <div className="my-2">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-black font-mono tracking-tight text-sky-300">
                  {fmt(projectedNextYearMean, 1)}
                </span>
                <span className="text-xs font-bold text-slate-300 font-mono">
                  {v.unit} [±{fmt(forecastMargin, 1)}]
                </span>
              </div>

              <p className="text-xs text-slate-300 mt-1 font-medium">
                {isWarmingOrIncrease
                  ? `Expected to continue upward drift with ±${fmt(forecastMargin, 1)} ${v.unit} seasonal spread.`
                  : `Projected stable/cooling trajectory with ±${fmt(forecastMargin, 1)} ${v.unit} seasonal spread.`}
              </p>
            </div>

            <span className="text-[10px] text-slate-400 font-medium">
              Outlook answers: <em>What is the forward risk?</em>
            </span>
          </div>
        </section>

        {/* ================= 3. SINGLE HERO CHART (Stagger 3) ================= */}
        <section className="stagger-3 dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col gap-3 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-white/10">
            <div className="flex items-center gap-2">
              <h2 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                <span>Climate Evolution & 1-Year Shaded Forecast</span>
              </h2>
              <span className="text-[10px] font-mono text-slate-400">
                {filteredSeries.length} Months Historical + 12 Months Predictive Horizon
              </span>
            </div>

            {/* Optional Secondary Overlay Toggles (Off by default) */}
            <div className="flex items-center gap-1.5 text-xs font-semibold">
              <button
                onClick={() => setShowMovingAvg((prev) => !prev)}
                className={`px-2.5 py-1 rounded-xl text-[10.5px] border transition-all ${
                  showMovingAvg
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-bold shadow-sm"
                    : "dark-clay-button text-slate-400 hover:text-white"
                }`}
              >
                12M Moving Avg
              </button>

              <button
                onClick={() => setShowHotspots((prev) => !prev)}
                className={`px-2.5 py-1 rounded-xl text-[10.5px] border transition-all ${
                  showHotspots
                    ? "bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold shadow-sm"
                    : "dark-clay-button text-slate-400 hover:text-white"
                }`}
              >
                Extreme Hotspots
              </button>
            </div>
          </div>

          {/* SVG Line Chart with Forecast Band & Dashed Divider */}
          <div className="dark-clay-inset rounded-2xl p-2 sm:p-3 relative">
            <LineChart
              series={chartSeries}
              band={forecastBand}
              unit={v.unit}
              height={260}
              forecastStartX={forecastStartX}
            />

            {/* Chart Legend & Explanation */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 mt-2 border-t border-white/10 text-[10.5px] font-mono text-slate-300">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-[#38bdf8]" /> Historical Observations (NASA POWER)
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-[#f59e0b] border-t border-dashed" /> Linear Climate Trend
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-2 bg-[#38bdf8]/30 rounded-xs" /> 1-Year Forecast Envelope (95% CI)
                </span>
              </div>

              {showHotspots && (
                <span className="text-rose-400 font-bold">
                  Hotspots active: highlighting observations with anomaly &gt; 1.5σ
                </span>
              )}
            </div>
          </div>
        </section>

        {/* ================= 4. AI INSIGHT & ACTION BAR (Stagger 4) ================= */}
        <section className="stagger-4 dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col md:flex-row items-center justify-between gap-4 shadow-xl border border-sky-500/20">
          {/* 3-Bullet Plain-English Summary */}
          <div className="flex-1 space-y-1.5 text-xs text-slate-200">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
                AI Detective Synthesis
              </span>
              <span className="text-[11px] text-slate-400 font-semibold">
                Answering the 4 Core Planetary Questions
              </span>
            </div>

            <div className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0 mt-1.5" />
              <p>
                <strong>What & Where: </strong>
                {v.name} in <strong className="text-white">{region.name}</strong> is exhibiting a persistent{" "}
                <span className={isWarmingOrIncrease ? "text-amber-400 font-bold" : "text-sky-400 font-bold"}>
                  {t.direction} {isWarmingOrIncrease ? "warming" : "cooling"}
                </span>{" "}
                trajectory across the continuous {t.period.years}-year satellite record.
              </p>
            </div>

            <div className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 mt-1.5" />
              <p>
                <strong>How Much & Significance: </strong>
                The empirical rate of change is{" "}
                <strong className="text-white">{signed(slopeDecade)} {v.unit}/decade</strong> (
                {signed(t.totalChange, 1)} {v.unit} total shift), which is mathematically confirmed to be{" "}
                <strong className={isSignificant ? "text-emerald-400" : "text-amber-400"}>
                  {isSignificant ? "statistically significant (p < 0.05)" : "within expected baseline noise"}
                </strong>.
              </p>
            </div>

            <div className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 shrink-0 mt-1.5" />
              <p>
                <strong>1-Year Outlook: </strong>
                Projected next-year baseline averages <strong className="text-white">{fmt(projectedNextYearMean, 1)} {v.unit}</strong>, elevating seasonal risks for water resource balance, agricultural heat stress, and civil infrastructure planning.
              </p>
            </div>
          </div>

          {/* Action Button: Open/Focus RAG AI Assistant */}
          <div className="flex flex-col sm:flex-row items-center gap-2 shrink-0 w-full md:w-auto">
            <button
              onClick={() => setIsAssistantOpen(true)}
              className="w-full md:w-auto dark-clay-button bg-gradient-to-r from-sky-600 to-blue-600 hover:brightness-110 text-white font-bold text-xs px-4 py-2.5 rounded-2xl flex items-center justify-center gap-2 shadow-lg active:scale-95 border border-sky-400/40 cursor-pointer"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>Ask AI Assistant About {region.name}</span>
            </button>

            <Link
              href={`/forecast?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(
                region.name
              )}&variable=${v.key}&horizon=5`}
              className="w-full md:w-auto dark-clay-button px-3.5 py-2.5 rounded-2xl text-xs font-bold text-slate-300 hover:text-white flex items-center justify-center gap-1.5 transition-all text-center"
            >
              <span>Multi-Year Scenarios</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </Link>
          </div>
        </section>

        {/* Pop-up RAG AI Assistant modal pre-seeded with this region's context */}
        {isAssistantOpen && (
          <div className="fixed bottom-6 right-6 sm:bottom-8 sm:right-8 z-50 w-84 sm:w-96 max-w-[calc(100vw-2rem)] h-[540px] max-h-[calc(100vh-100px)] flex flex-col shadow-2xl animate-[fadeInUp_0.3s_ease-out]">
            <AiAssistantTemplate
              selectedCountry={countryObj}
              onClose={() => setIsAssistantOpen(false)}
            />
          </div>
        )}
      </div>
    </PageFrame>
  );
}

function Dashboard({ sel }: { sel: Selection }) {
  const { data, error, retry: load } = useAsync(
    () => fetchAnalysis(sel),
    selectionToParams(sel).toString()
  );

  const title = `${sel.name}`;
  if (error) {
    return (
      <PageFrame title={title} subtitle="Dashboard" noScroll={false} theme="clay">
        <ErrorBox message={error} onRetry={load} />
      </PageFrame>
    );
  }
  if (!data) {
    return (
      <PageFrame title={title} subtitle="Dashboard" noScroll={false} theme="clay">
        <Loading text="Retrieving NASA satellite observations and computing trend..." />
      </PageFrame>
    );
  }

  return <DashboardContent data={data} sel={sel} />;
}

export default function DashboardView() {
  const sp = useSearchParams();
  const sel =
    parseSelection(sp) ?? {
      lat: 31.95,
      lon: 35.23,
      name: "Palestine",
      variable: "T2M",
      start: 1990,
      end: 2025,
    };
  return (
    <Suspense fallback={<Loading text="Loading NASA Dashboard..." />}>
      <Dashboard sel={sel} />
    </Suspense>
  );
}