"use client";

import React, { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAsync } from "../lib/useAsync";
import PageFrame, { ErrorBox, Loading } from "./PageFrame";
import AiAssistantTemplate from "./AiAssistantTemplate";
import {
  fetchAnalysis,
  fetchForecast,
  parseSelection,
  selectionToParams,
  type Selection,
  type AnalysisResult,
} from "../lib/api-client";
import { VARIABLES, EXAMPLES } from "../lib/catalog";
import { COUNTRIES, Country } from "../data/countries";

const CHAPTERS = [
  {
    num: 1,
    title: "Meet the Location & Data Trust",
    subtitle: "What is the normal baseline of this place?",
    buttonLabel: "See how it changed over time →",
  },
  {
    num: 2,
    title: "The Bumps & Extremes",
    subtitle: "Are weather fluctuations steady or wild swings?",
    buttonLabel: "Is this just ups & downs, or a real trend? →",
  },
  {
    num: 3,
    title: "The Detective Verdict",
    subtitle: "Is the shift mathematically real or random noise?",
    buttonLabel: "What patterns are repeating? →",
  },
  {
    num: 4,
    title: "The Rhythm of Seasons",
    subtitle: "Separating the seasonal heartbeat from genuine change.",
    buttonLabel: "What happens next? (Forecast & Outlook) →",
  },
  {
    num: 5,
    title: "The Future Horizon & AI Detective",
    subtitle: "Verified predictive horizon & planetary risk action.",
    buttonLabel: "Simulate Multi-Year Scenarios →",
  },
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

/** "YYYY-MM" to decimal year mid-month */
function dateToDecYear(d: string): number {
  return Number(d.slice(0, 4)) + (Number(d.slice(5, 7)) - 0.5) / 12;
}

// =========================================================================
// ZERO FAKE DATA: DISCOVERY HUB LAUNCHER (When user hasn't chosen a region yet)
// =========================================================================
function TargetDiscoveryLauncher() {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const filteredCountries = useMemo(() => {
    if (!search.trim()) return COUNTRIES.slice(0, 8);
    const q = search.toLowerCase();
    return COUNTRIES.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.officialName.toLowerCase().includes(q) ||
        c.region.toLowerCase().includes(q)
    ).slice(0, 12);
  }, [search]);

  return (
    <PageFrame
      title="EarthTrend Detective: Investigation Launcher"
      subtitle="Select a global Earth observation site to begin investigation"
      noScroll={false}
      maxWidth="max-w-5xl"
      theme="clay"
      hideHeader={true}
    >
      <div className="w-full flex flex-col items-center justify-center py-8 px-4 text-center">
        {/* Logo and Welcome Badge */}
        <div className="relative w-16 h-16 rounded-2xl overflow-hidden border border-amber-400/50 bg-black shadow-[0_0_30px_rgba(245,158,11,0.35)] flex items-center justify-center mb-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.jpg" alt="Logo" className="w-full h-full object-contain" />
        </div>

        <span className="text-xs font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 mb-2">
          Guided Detective Mode • Zero Fake Data
        </span>

        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight max-w-lg mb-2">
          Choose an Earth Observation Target
        </h1>
        <p className="text-sm text-slate-300 max-w-xl leading-relaxed mb-6">
          Every screen starts empty until you select a real-world location or grid point. We connect directly to NASA satellite archives (POWER, MERRA-2, CERES) to evaluate planetary shifts step-by-step.
        </p>

        {/* 5 NASA Official Challenge Demonstration Examples */}
        <div className="w-full max-w-3xl mb-8 p-4 rounded-3xl bg-[#080d16]/90 border border-amber-500/30 shadow-2xl text-left">
          <div className="flex items-center justify-between mb-3 border-b border-white/10 pb-2">
            <span className="text-xs font-bold text-amber-300 uppercase tracking-wider font-mono flex items-center gap-2">
              <span>🚀</span>
              <span>NASA Space Apps 5 Challenge Demonstration Scenarios</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Click to launch investigation</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.slug}
                onClick={() => {
                  router.push(
                    `/dashboard?lat=${ex.lat}&lon=${ex.lon}&name=${encodeURIComponent(
                      ex.region_name
                    )}&variable=${ex.variable_key}&start=${ex.start_year}&end=${ex.end_year}`
                  );
                }}
                className="p-3 rounded-2xl bg-white/5 hover:bg-amber-500/15 border border-white/10 hover:border-amber-400/50 transition-all text-left flex flex-col justify-between gap-2 group cursor-pointer"
              >
                <div>
                  <div className="flex items-center justify-between gap-1 text-xs font-bold text-white group-hover:text-amber-300 transition-colors">
                    <span>{ex.title}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/10 text-slate-300">
                      {ex.variable_key}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">
                    {ex.story}
                  </p>
                </div>
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1 border-t border-white/5">
                  <span>{ex.region_name}, {ex.country ?? "Region"}</span>
                  <span className="text-amber-400 group-hover:translate-x-1 transition-transform">Launch →</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Search input for points or countries */}
        <div className="w-full max-w-md relative mb-6">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search region, country, or enter coordinates (lat, lon)..."
            className="w-full bg-[#0a111c] border border-white/15 focus:border-amber-400 rounded-2xl px-4 py-3 text-sm text-white placeholder-slate-500 outline-none shadow-lg transition-all"
          />
          <div className="absolute right-3.5 top-3.5 text-slate-400">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>
        </div>

        {/* Preset quick target grid */}
        <div className="w-full max-w-3xl grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-8">
          {filteredCountries.map((c) => (
            <button
              key={c.id}
              onClick={() => {
                router.push(
                  `/dashboard?lat=${c.lat}&lon=${c.lng}&name=${encodeURIComponent(
                    c.name
                  )}&variable=T2M&start=1990&end=2024`
                );
              }}
              className="p-3 rounded-2xl bg-[#080d16]/80 hover:bg-white/10 border border-white/10 hover:border-amber-400/50 text-left transition-all group flex flex-col justify-between cursor-pointer"
            >
              <div>
                <span className="text-xs font-bold text-white group-hover:text-amber-300 block truncate">
                  {c.name}
                </span>
                <span className="text-[10px] text-slate-400 block truncate font-mono">
                  {c.capital}
                </span>
              </div>
              <span className="text-[10px] text-slate-500 font-mono mt-2 block">
                {c.lat > 0 ? `${c.lat.toFixed(1)}°N` : `${Math.abs(c.lat).toFixed(1)}°S`},{" "}
                {c.lng > 0 ? `${c.lng.toFixed(1)}°E` : `${Math.abs(c.lng).toFixed(1)}°W`}
              </span>
            </button>
          ))}
        </div>

        {/* 3D Globe Direct Link */}
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/"
            className="cosmic-gold-button px-5 py-2.5 rounded-2xl text-xs font-bold flex items-center gap-2 shadow-lg cursor-pointer"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="2" y1="12" x2="22" y2="12"></line>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
            </svg>
            <span>Fly to 3D Globe to Pick Any Coordinate</span>
          </Link>

          <Link
            href="/chat"
            className="dark-clay-button px-4 py-2.5 rounded-2xl text-xs font-bold text-slate-300 hover:text-white flex items-center gap-2 transition-all cursor-pointer"
          >
            <div className="w-4 h-4 rounded-full overflow-hidden bg-black shrink-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.jpg" alt="AI" className="w-full h-full object-contain" />
            </div>
            <span>Ask AI Detective</span>
          </Link>
        </div>
      </div>
    </PageFrame>
  );
}

// =========================================================================
// INTERACTIVE CINEMATIC STAGE (Dynamic Animated Explainer Chart Canvas)
// =========================================================================
interface StageProps {
  chapter: number;
  data: AnalysisResult;
  future12Months: { x: number; y: number; lower: number; upper: number }[];
  normalRange: {
    min: number;
    max: number;
    mean: number;
    median: number;
    p10: number;
    p90: number;
  };
}

function CinematicStage({ chapter, data, future12Months, normalRange }: StageProps) {
  const { series, trend: t, variable: v } = data;
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // SVG Stage Dimensions
  const W = 760;
  const H = 340;
  const PAD = { t: 25, r: 25, b: 40, l: 55 };

  // Domain scaling
  const minX = dateToDecYear(series[0].date);
  const maxX =
    chapter === 5 && future12Months.length > 0
      ? future12Months[future12Months.length - 1].x
      : dateToDecYear(series[series.length - 1].date);

  const allVals = series.map((s) => s.value);
  if (chapter === 5 && future12Months.length > 0) {
    future12Months.forEach((p) => {
      allVals.push(p.lower, p.upper, p.y);
    });
  }

  const rawMinY = Math.min(...allVals);
  const rawMaxY = Math.max(...allVals);
  const padY = Math.max(0.2, (rawMaxY - rawMinY) * 0.12);
  const minY = rawMinY - padY;
  const maxY = rawMaxY + padY;

  const sx = (x: number) => PAD.l + ((x - minX) / (maxX - minX || 1)) * (W - PAD.l - PAD.r);
  const sy = (y: number) => H - PAD.b - ((y - minY) / (maxY - minY || 1)) * (H - PAD.t - PAD.b);

  // Path 1: Historical Monthly Series
  const historicalPath = series
    .map((s, i) => `${i === 0 ? "M" : "L"} ${sx(dateToDecYear(s.date))} ${sy(s.value)}`)
    .join(" ");

  // Path 2: Linear Trend Line (Chapter 3)
  const firstPt = series[0];
  const lastPoint = series[series.length - 1];
  const trendLinePath = `M ${sx(dateToDecYear(firstPt.date))} ${sy(firstPt.trend)} L ${sx(
    dateToDecYear(lastPoint.date)
  )} ${sy(lastPoint.trend)}`;

  // Path 3: Confidence Interval Ribbon (Chapter 3)
  const ciMargin = Math.max(0.15, Math.abs(t.ols.ci95[1] - t.ols.ci95[0]) * 0.5);
  const ciTop = `M ${sx(dateToDecYear(firstPt.date))} ${sy(firstPt.trend + ciMargin)} L ${sx(
    dateToDecYear(lastPoint.date)
  )} ${sy(lastPoint.trend + ciMargin)}`;
  const ciBottom = `L ${sx(dateToDecYear(lastPoint.date))} ${sy(
    lastPoint.trend - ciMargin
  )} L ${sx(dateToDecYear(firstPt.date))} ${sy(firstPt.trend - ciMargin)} Z`;
  const ciBandPath = `${ciTop} ${ciBottom}`;

  // Path 4: Seasonal Rhythm Cycle (Chapter 4)
  const seasonalPath = series
    .map((s, i) => {
      const monthIdx = (Number(s.date.slice(5, 7)) - 1) % 12;
      const clim = t.seasonalClimatology[monthIdx >= 0 ? monthIdx : 0];
      return `${i === 0 ? "M" : "L"} ${sx(dateToDecYear(s.date))} ${sy(s.trend + (clim - t.mean))}`;
    })
    .join(" ");

  // Path 5: Forecast Trajectory & Uncertainty Envelope (Chapter 5)
  const lastDecX = dateToDecYear(lastPoint.date);
  const forecastLinePath = [
    `M ${sx(lastDecX)} ${sy(lastPoint.value)}`,
    ...future12Months.map((p) => `L ${sx(p.x)} ${sy(p.y)}`),
  ].join(" ");

  const forecastUpper = [
    `M ${sx(lastDecX)} ${sy(lastPoint.value)}`,
    ...future12Months.map((p) => `L ${sx(p.x)} ${sy(p.upper)}`),
  ].join(" ");
  const forecastLower = [
    ...future12Months.slice().reverse().map((p) => `L ${sx(p.x)} ${sy(p.lower)}`),
    `L ${sx(lastDecX)} ${sy(lastPoint.value)} Z`,
  ].join(" ");
  const forecastBandPath = `${forecastUpper} ${forecastLower}`;

  // Extremes for Chapter 2
  const extremes = series.filter(
    (s) => Math.abs(s.anomaly) > t.stdDev * 1.5 || s.value >= normalRange.p90 || s.value <= normalRange.p10
  );

  // X-axis ticks (every 5-10 years)
  const startYr = Number(series[0].date.slice(0, 4));
  const endYr = Number(series[series.length - 1].date.slice(0, 4));
  const yearStep = endYr - startYr > 20 ? 5 : 2;
  const xTicks: number[] = [];
  for (let yr = Math.ceil(startYr / yearStep) * yearStep; yr <= endYr + 1; yr += yearStep) {
    xTicks.push(yr);
  }

  // Y-axis ticks
  const yRange = maxY - minY;
  const yStep = yRange > 20 ? 10 : yRange > 8 ? 5 : yRange > 3 ? 2 : 1;
  const yTicks: number[] = [];
  for (let y = Math.ceil(minY / yStep) * yStep; y <= maxY; y += yStep) {
    yTicks.push(y);
  }

  return (
    <div className="relative w-full dark-clay-inset rounded-2xl sm:rounded-3xl p-3 sm:p-4 overflow-hidden border border-white/10 shadow-2xl">
      {/* Stage Header Info Overlay */}
      <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-white/10 text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_#f59e0b]"></span>
          <span className="font-bold text-white">Interactive Stage Canvas</span>
          <span className="text-slate-400">• Chapter {chapter}: {CHAPTERS[chapter - 1].title}</span>
        </div>
        <div className="text-[11px] text-slate-400">
          Continuous Monthly Observations ({v.unit})
        </div>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto select-none overflow-visible"
        onMouseLeave={() => setHoverIndex(null)}
      >
        {/* Background Grids */}
        {yTicks.map((yVal) => (
          <g key={yVal}>
            <line
              x1={PAD.l}
              x2={W - PAD.r}
              y1={sy(yVal)}
              y2={sy(yVal)}
              stroke="#ffffff"
              strokeOpacity="0.08"
              strokeDasharray="3 3"
            />
            <text
              x={PAD.l - 8}
              y={sy(yVal) + 3.5}
              textAnchor="end"
              fill="#94a3b8"
              fontSize="10"
              fontFamily="monospace"
            >
              {fmt(yVal, 1)}
            </text>
          </g>
        ))}

        {xTicks.map((xVal) => (
          <g key={xVal}>
            <line
              x1={sx(xVal)}
              x2={sx(xVal)}
              y1={PAD.t}
              y2={H - PAD.b}
              stroke="#ffffff"
              strokeOpacity="0.05"
            />
            <text
              x={sx(xVal)}
              y={H - 12}
              textAnchor="middle"
              fill="#94a3b8"
              fontSize="10"
              fontFamily="monospace"
            >
              {xVal}
            </text>
          </g>
        ))}

        {/* -------------------------------------------------------------
            CHAPTER 1: NORMAL RANGE HORIZONTAL BAND (Mean, Median, Min/Max)
           ------------------------------------------------------------- */}
        <rect
          x={PAD.l}
          y={sy(normalRange.max)}
          width={W - PAD.l - PAD.r}
          height={Math.max(4, sy(normalRange.min) - sy(normalRange.max))}
          fill="#38bdf8"
          fillOpacity={chapter === 1 ? "0.14" : "0.05"}
          className="transition-all duration-700"
        />

        {/* Mean reference dashed line */}
        <line
          x1={PAD.l}
          x2={W - PAD.r}
          y1={sy(normalRange.mean)}
          y2={sy(normalRange.mean)}
          stroke="#38bdf8"
          strokeWidth="1.5"
          strokeDasharray="6 4"
          strokeOpacity={chapter === 1 ? "0.9" : "0.3"}
        />

        {/* Median reference line */}
        <line
          x1={PAD.l}
          x2={W - PAD.r}
          y1={sy(normalRange.median)}
          y2={sy(normalRange.median)}
          stroke="#38bdf8"
          strokeWidth="1"
          strokeDasharray="2 3"
          strokeOpacity={chapter === 1 ? "0.85" : "0.2"}
        />

        {/* -------------------------------------------------------------
            CHAPTER 3: CONFIDENCE INTERVAL & BOLD TREND ARROW
           ------------------------------------------------------------- */}
        {chapter >= 3 && (
          <g className="animate-[fadeInUp_0.5s_ease-out]">
            <path d={ciBandPath} fill="#f59e0b" fillOpacity="0.18" />
            <path
              d={trendLinePath}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2.8"
              strokeLinecap="round"
              className="drop-shadow-[0_0_8px_rgba(245,158,11,0.6)]"
            />
          </g>
        )}

        {/* -------------------------------------------------------------
            CHAPTER 4: SEASONAL HARMONIC RHYTHM
           ------------------------------------------------------------- */}
        {chapter === 4 && (
          <g className="animate-[fadeInUp_0.5s_ease-out]">
            <path
              d={seasonalPath}
              fill="none"
              stroke="#10b981"
              strokeWidth="2.2"
              className="drop-shadow-[0_0_6px_rgba(16,185,129,0.5)]"
            />
          </g>
        )}

        {/* -------------------------------------------------------------
            CHAPTER 2+: HISTORICAL TIME SERIES (Animated drawing)
           ------------------------------------------------------------- */}
        {chapter >= 2 && (
          <g>
            <path
              d={historicalPath}
              fill="none"
              stroke="#38bdf8"
              strokeWidth={chapter === 2 ? 2.2 : 1.4}
              strokeOpacity={chapter === 3 ? 0.3 : 0.85}
              className={`transition-all duration-500 ${chapter === 2 ? "animate-draw-line" : ""}`}
            />
          </g>
        )}

        {/* -------------------------------------------------------------
            CHAPTER 2: EXTREME PEAKS & VALLEYS PULSING MARKERS
           ------------------------------------------------------------- */}
        {chapter === 2 && (
          <g className="animate-[fadeInUp_0.6s_ease-out]">
            {extremes.map((s, idx) => (
              <g key={idx}>
                <circle
                  cx={sx(dateToDecYear(s.date))}
                  cy={sy(s.value)}
                  r="7"
                  fill="none"
                  stroke={s.value > normalRange.mean ? "#f59e0b" : "#38bdf8"}
                  strokeWidth="1.5"
                  className="pulse-glow"
                />
                <circle
                  cx={sx(dateToDecYear(s.date))}
                  cy={sy(s.value)}
                  r="3"
                  fill={s.value > normalRange.mean ? "#f59e0b" : "#38bdf8"}
                />
              </g>
            ))}
          </g>
        )}

        {/* -------------------------------------------------------------
            CHAPTER 5: FORECAST EXTENSION & UNCERTAINTY BAND
           ------------------------------------------------------------- */}
        {chapter === 5 && (
          <g className="animate-[fadeInUp_0.6s_ease-out]">
            {/* Forecast start divider */}
            <line
              x1={sx(dateToDecYear(lastPoint.date))}
              x2={sx(dateToDecYear(lastPoint.date))}
              y1={PAD.t}
              y2={H - PAD.b}
              stroke="#f59e0b"
              strokeWidth="1.5"
              strokeDasharray="4 4"
            />
            {/* Forecast shaded envelope */}
            <path d={forecastBandPath} fill="#f59e0b" fillOpacity="0.25" />
            {/* Forecast center trajectory */}
            <path
              d={forecastLinePath}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2.5"
              strokeDasharray="5 4"
              className="drop-shadow-[0_0_8px_rgba(245,158,11,0.6)]"
            />
            <text
              x={sx(dateToDecYear(lastPoint.date)) + 8}
              y={PAD.t + 16}
              fill="#f59e0b"
              fontSize="10"
              fontWeight="bold"
              fontFamily="monospace"
            >
              Predictive Outlook Envelope →
            </text>
          </g>
        )}

        {/* Interactive hover scrubber */}
        {chapter >= 2 &&
          series.map((s, i) => (
            <rect
              key={i}
              x={sx(dateToDecYear(s.date)) - 2}
              y={PAD.t}
              width={Math.max(4, W / series.length)}
              height={H - PAD.t - PAD.b}
              fill="transparent"
              className="cursor-crosshair"
              onMouseEnter={() => setHoverIndex(i)}
            />
          ))}

        {hoverIndex !== null && series[hoverIndex] && (
          <g>
            <line
              x1={sx(dateToDecYear(series[hoverIndex].date))}
              x2={sx(dateToDecYear(series[hoverIndex].date))}
              y1={PAD.t}
              y2={H - PAD.b}
              stroke="#ffffff"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
            <circle
              cx={sx(dateToDecYear(series[hoverIndex].date))}
              cy={sy(series[hoverIndex].value)}
              r="4.5"
              fill="#ffffff"
              stroke="#f59e0b"
              strokeWidth="2"
            />
          </g>
        )}
      </svg>

      {/* Hover Value Tooltip HUD */}
      {hoverIndex !== null && series[hoverIndex] && (
        <div className="absolute top-4 right-4 bg-[#0a111c]/95 border border-amber-400/50 rounded-xl px-3 py-1.5 shadow-xl text-xs font-mono flex items-center gap-3 backdrop-blur-md">
          <span className="text-slate-300 font-bold">{series[hoverIndex].date}</span>
          <span className="text-amber-300 font-black">
            {fmt(series[hoverIndex].value, 2)} {v.unit}
          </span>
          <span className="text-slate-400 text-[10px]">
            (Anomaly: {signed(series[hoverIndex].anomaly, 2)})
          </span>
        </div>
      )}
    </div>
  );
}

// =========================================================================
// SIDE-BY-SIDE COMPARATIVE STAGE (Region A vs Region B for Same Variable)
// =========================================================================
interface CompareStageProps {
  dataA: AnalysisResult;
  dataB: AnalysisResult;
}

function ComparativeStage({ dataA, dataB }: CompareStageProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const seriesA = dataA.series;
  const seriesB = dataB.series;
  const v = dataA.variable;

  const W = 760;
  const H = 340;
  const PAD = { t: 25, r: 25, b: 40, l: 55 };

  const minXA = dateToDecYear(seriesA[0].date);
  const maxXA = dateToDecYear(seriesA[seriesA.length - 1].date);
  const minXB = dateToDecYear(seriesB[0].date);
  const maxXB = dateToDecYear(seriesB[seriesB.length - 1].date);

  const minX = Math.min(minXA, minXB);
  const maxX = Math.max(maxXA, maxXB);

  const allVals = [...seriesA.map((s) => s.value), ...seriesB.map((s) => s.value)];
  const rawMinY = Math.min(...allVals);
  const rawMaxY = Math.max(...allVals);
  const padY = Math.max(0.2, (rawMaxY - rawMinY) * 0.12);
  const minY = rawMinY - padY;
  const maxY = rawMaxY + padY;

  const sx = (x: number) => PAD.l + ((x - minX) / (maxX - minX || 1)) * (W - PAD.l - PAD.r);
  const sy = (y: number) => H - PAD.b - ((y - minY) / (maxY - minY || 1)) * (H - PAD.t - PAD.b);

  const pathA = seriesA
    .map((s, i) => `${i === 0 ? "M" : "L"} ${sx(dateToDecYear(s.date))} ${sy(s.value)}`)
    .join(" ");

  const pathB = seriesB
    .map((s, i) => `${i === 0 ? "M" : "L"} ${sx(dateToDecYear(s.date))} ${sy(s.value)}`)
    .join(" ");

  const trendA = `M ${sx(dateToDecYear(seriesA[0].date))} ${sy(seriesA[0].trend)} L ${sx(
    dateToDecYear(seriesA[seriesA.length - 1].date)
  )} ${sy(seriesA[seriesA.length - 1].trend)}`;

  const trendB = `M ${sx(dateToDecYear(seriesB[0].date))} ${sy(seriesB[0].trend)} L ${sx(
    dateToDecYear(seriesB[seriesB.length - 1].date)
  )} ${sy(seriesB[seriesB.length - 1].trend)}`;

  return (
    <div className="relative w-full dark-clay-inset rounded-2xl sm:rounded-3xl p-3 sm:p-4 overflow-hidden border border-white/10 shadow-2xl">
      <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-white/10 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <span className="font-bold text-amber-300">{dataA.region.name} (Region A)</span>
          </div>
          <span className="text-slate-500">vs</span>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
            <span className="font-bold text-sky-300">{dataB.region.name} (Region B)</span>
          </div>
        </div>
        <div className="text-[11px] text-slate-400">
          Comparing {v.name} ({v.unit})
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none overflow-visible">
        {/* Horizontal grid lines */}
        {[minY, (minY + maxY) / 2, maxY].map((yVal, idx) => (
          <g key={idx}>
            <line
              x1={PAD.l}
              x2={W - PAD.r}
              y1={sy(yVal)}
              y2={sy(yVal)}
              stroke="#ffffff"
              strokeOpacity="0.08"
              strokeDasharray="3 3"
            />
            <text x={PAD.l - 8} y={sy(yVal) + 3.5} textAnchor="end" fill="#94a3b8" fontSize="10" fontFamily="monospace">
              {fmt(yVal, 1)}
            </text>
          </g>
        ))}

        {/* Region A line & trend */}
        <path d={pathA} fill="none" stroke="#f59e0b" strokeWidth="2.2" strokeOpacity="0.9" />
        <path d={trendA} fill="none" stroke="#f59e0b" strokeWidth="2.5" strokeDasharray="6 4" />

        {/* Region B line & trend */}
        <path d={pathB} fill="none" stroke="#38bdf8" strokeWidth="2.2" strokeOpacity="0.9" />
        <path d={trendB} fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeDasharray="6 4" />

        {/* Interactive scrubber */}
        {seriesA.map((s, i) => (
          <rect
            key={i}
            x={sx(dateToDecYear(s.date)) - 2}
            y={PAD.t}
            width={Math.max(4, W / seriesA.length)}
            height={H - PAD.t - PAD.b}
            fill="transparent"
            className="cursor-crosshair"
            onMouseEnter={() => setHoverIndex(i)}
          />
        ))}

        {hoverIndex !== null && seriesA[hoverIndex] && (
          <g>
            <line
              x1={sx(dateToDecYear(seriesA[hoverIndex].date))}
              x2={sx(dateToDecYear(seriesA[hoverIndex].date))}
              y1={PAD.t}
              y2={H - PAD.b}
              stroke="#ffffff"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
            <circle cx={sx(dateToDecYear(seriesA[hoverIndex].date))} cy={sy(seriesA[hoverIndex].value)} r="4" fill="#f59e0b" />
            {seriesB[hoverIndex] && (
              <circle cx={sx(dateToDecYear(seriesB[hoverIndex].date))} cy={sy(seriesB[hoverIndex].value)} r="4" fill="#38bdf8" />
            )}
          </g>
        )}
      </svg>

      {/* Scrubber Tooltip */}
      {hoverIndex !== null && seriesA[hoverIndex] && (
        <div className="absolute top-4 right-4 bg-[#0a111c]/95 border border-white/20 rounded-xl px-3 py-1.5 shadow-xl text-xs font-mono flex items-center gap-4 backdrop-blur-md">
          <span className="text-slate-300 font-bold">{seriesA[hoverIndex].date}</span>
          <span className="text-amber-300 font-bold">
            {dataA.region.name}: {fmt(seriesA[hoverIndex].value, 2)} {v.unit}
          </span>
          {seriesB[hoverIndex] && (
            <span className="text-sky-300 font-bold">
              {dataB.region.name}: {fmt(seriesB[hoverIndex].value, 2)} {v.unit}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// =========================================================================
// MAIN GUIDED DETECTIVE DASHBOARD CONTROLLER
// =========================================================================
export function DashboardView() {
  const searchParams = useSearchParams();
  const sel = parseSelection(searchParams);

  if (!sel) {
    return <TargetDiscoveryLauncher />;
  }

  return <DashboardLoadedView sel={sel} />;
}

function DashboardLoadedView({ sel }: { sel: Selection }) {
  const router = useRouter();
  const selKey = `${sel.lat},${sel.lon},${sel.variable},${sel.start},${sel.end}`;
  const { data, error, retry } = useAsync(() => fetchAnalysis(sel), selKey);
  const loading = !data && !error;

  // Guided Detective Chapter State (1 to 5)
  const [chapter, setChapter] = useState<number>(1);
  const [scientistView, setScientistView] = useState<boolean>(false);
  const [isVariablesModalOpen, setIsVariablesModalOpen] = useState<boolean>(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState<boolean>(false);

  // Side-by-Side Comparison Mode State
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [compareRegion, setCompareRegion] = useState<{ lat: number; lon: number; name: string }>({
    lat: 78.2,
    lon: 15.6,
    name: "Svalbard",
  });
  const compKey = isComparing && compareRegion
    ? `${compareRegion.lat},${compareRegion.lon},${sel.variable},${sel.start},${sel.end}`
    : "none";
  const { data: compareData, error: compareError, retry: retryCompare } = useAsync(
    () =>
      isComparing && compareRegion
        ? fetchAnalysis({
            lat: compareRegion.lat,
            lon: compareRegion.lon,
            name: compareRegion.name,
            variable: sel.variable,
            start: sel.start,
            end: sel.end,
          })
        : Promise.resolve(null),
    compKey
  );
  const compareLoading = isComparing && !compareData && !compareError;

  // Forecast state for Chapter 5 calling /api/forecast
  const [forecastHorizon, setForecastHorizon] = useState<number>(5);
  const forecastKey =
    chapter === 5
      ? `${sel.lat},${sel.lon},${sel.variable},${sel.start},${sel.end},${forecastHorizon}`
      : "disabled";
  const { data: apiForecast, error: forecastError } = useAsync(
    () => (chapter === 5 ? fetchForecast(sel, forecastHorizon) : Promise.resolve(null)),
    forecastKey
  );
  const forecastLoading = chapter === 5 && !apiForecast && !forecastError;

  if (loading || !data) {
    return (
      <PageFrame title="NASA EarthTrend Detective" subtitle="Querying satellite observations..." noScroll={false} theme="clay">
        <Loading text="Querying NASA POWER, MERRA-2 & CERES satellite archive..." />
      </PageFrame>
    );
  }

  if (error) {
    return (
      <PageFrame title="NASA EarthTrend Detective" subtitle="Error" noScroll={false} theme="clay">
        <ErrorBox message={error} onRetry={retry} />
      </PageFrame>
    );
  }

  const { trend: t, variable: v, region, series } = data;

  // Calculate descriptive statistics
  const values = series.map((s: { value: number }) => s.value).sort((a: number, b: number) => a - b);
  const normalRange = {
    min: t.min.value,
    max: t.max.value,
    mean: t.mean,
    median:
      values.length % 2 === 0
        ? (values[values.length / 2 - 1] + values[values.length / 2]) / 2
        : values[Math.floor(values.length / 2)],
    p10: values[Math.floor(values.length * 0.1)] ?? values[0],
    p90: values[Math.floor(values.length * 0.9)] ?? values[values.length - 1],
  };

  const slopeDecade = t.ols.slopePerYear * 10;
  const isWarmingOrIncrease = t.ols.slopePerYear > 0;
  const isSignificant = t.verdict === "significant";

  // Data completeness
  const expectedMonths = t.period.months || series.length;
  const reliabilityPct = Math.min(100, Math.round((series.length / expectedMonths) * 100));

  // Chapter 5 forecast points
  const lastPoint = series[series.length - 1];
  const lastDate = lastPoint?.date ?? `${t.period.end}-12`;
  const lastYear = Number(lastDate.slice(0, 4));
  const lastMonth = Number(lastDate.slice(5, 7));
  const climMean = t.seasonalClimatology.reduce((a: number, b: number) => a + b, 0) / 12;
  const forecastMargin = Math.max(0.2, 1.96 * (t.stdDev * 0.35 + Math.abs(t.ols.stdErr)));

  const future12Months =
    apiForecast?.forecast?.forecast?.length
      ? apiForecast.forecast.forecast.map((p) => {
          const yr = Number(p.date.slice(0, 4));
          const mo = Number(p.date.slice(5, 7));
          return {
            x: yr + (mo - 0.5) / 12,
            y: p.value,
            lower: p.lower,
            upper: p.upper,
          };
        })
      : Array.from({ length: 12 }, (_, idx) => {
          const m = idx + 1;
          const monthIdx = (lastMonth + m - 1) % 12;
          const seasonalShift = t.seasonalClimatology[monthIdx] - climMean;
          const futureDecimalYear = lastYear + (lastMonth + m - 0.5) / 12;
          const futureTrend = lastPoint.trend + t.ols.slopePerYear * (m / 12);
          const predictedVal = futureTrend + seasonalShift;
          const uncertaintyExpansion = forecastMargin * (1 + 0.04 * m);
          return {
            x: futureDecimalYear,
            y: predictedVal,
            lower: predictedVal - uncertaintyExpansion,
            upper: predictedVal + uncertaintyExpansion,
          };
        });

  // Country Object for AI Assistant
  const countryObj: Country = {
    id: region.name.toLowerCase().replace(/[^a-z0-9]/g, "-") || "grid-cell",
    name: region.name,
    officialName: region.name,
    code2: (region.country_code ?? "UN").slice(0, 2).toUpperCase(),
    code3: region.country_code ?? "CELL",
    region: "Asia",
    subregion: "Observation Target",
    capital: region.name,
    lat: region.lat,
    lng: region.lon,
    zoom: 2.2,
    population: "N/A",
    area: "0.5° × 0.5° Grid Cell",
    currency: "N/A",
    timezone: "UTC",
  };

  const isGridCell = region.name.startsWith("Grid Cell") || region.name.includes("°");

  return (
    <PageFrame
      title={`NASA EarthTrend Detective: ${region.name}`}
      subtitle={`${v.name} (${v.unit}) • Continuous Satellite Record`}
      noScroll={false}
      maxWidth="max-w-6xl"
      theme="clay"
      hideHeader={true}
    >
      <div className="w-full flex flex-col gap-4 py-3 px-2 sm:px-4 text-slate-100 font-sans select-none">
        {/* =========================================================================
            TOP NARRATIVE BAR & CHAPTER SCRUBBER
            ========================================================================= */}
        <header className="dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 flex flex-col gap-3 shadow-xl border border-white/10">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
            {/* Logo + Target Region */}
            <div className="flex items-center gap-3">
              <div className="relative w-10 h-10 rounded-xl overflow-hidden border border-amber-400/50 bg-black shadow-[0_0_15px_rgba(245,158,11,0.3)] shrink-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.jpg" alt="Logo" className="w-full h-full object-contain" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                    {isGridCell ? "NASA 0.5° Grid Cell" : "NASA Observation Site"}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    {region.lat > 0 ? `${region.lat.toFixed(1)}°N` : `${Math.abs(region.lat).toFixed(1)}°S`},{" "}
                    {region.lon > 0 ? `${region.lon.toFixed(1)}°E` : `${Math.abs(region.lon).toFixed(1)}°W`}
                  </span>
                </div>
                <h1 className="text-lg sm:text-2xl font-black text-white tracking-tight flex items-center gap-2">
                  <span>{region.name}</span>
                  <span className="text-sm font-normal text-slate-400">/ {v.name}</span>
                </h1>
              </div>
            </div>

            {/* Top Quick Actions: Variable Selector + Compare Mode + 3D Globe Link */}
            <div className="flex flex-wrap items-center gap-1.5">
              {/* Full 12 Variables & Period Modal Toggle */}
              <button
                onClick={() => setIsVariablesModalOpen(true)}
                className="px-3 py-1.5 rounded-xl text-xs font-bold cosmic-gold-button flex items-center gap-1.5 shadow-md active:scale-95 cursor-pointer"
              >
                <span>📊</span>
                <span>All 12 Variables & Period</span>
              </button>

              {/* Side-by-Side Comparison Toggle */}
              <button
                onClick={() => setIsComparing((prev) => !prev)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 border cursor-pointer ${
                  isComparing
                    ? "bg-sky-500 text-white border-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.5)]"
                    : "dark-clay-button text-slate-300 hover:text-white border-white/10"
                }`}
              >
                <span>⚖️</span>
                <span>{isComparing ? "Exit Comparison" : "Compare 2 Regions"}</span>
              </button>

              {/* Back to 3D Globe Link */}
              <Link
                href={`/?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(region.name)}`}
                className="dark-clay-button px-3 py-1.5 rounded-xl text-xs font-bold text-amber-300 hover:text-white flex items-center gap-1.5 transition-all border border-amber-500/30"
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

          {/* 5 NASA Official Challenge Demonstration Scenarios Strip */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 border-b border-white/5 pb-2 text-xs">
            <span className="text-[10px] font-mono text-amber-300/80 font-bold uppercase tracking-wider shrink-0">
              NASA 5 Demo Scenarios:
            </span>
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex.slug}
                  onClick={() => {
                    router.push(
                      `/dashboard?lat=${ex.lat}&lon=${ex.lon}&name=${encodeURIComponent(
                        ex.region_name
                      )}&variable=${ex.variable_key}&start=${ex.start_year}&end=${ex.end_year}`
                    );
                  }}
                  className={`px-2.5 py-1 rounded-xl text-[11px] font-semibold whitespace-nowrap transition-all border ${
                    region.name === ex.region_name && v.key === ex.variable_key
                      ? "bg-amber-500/25 text-amber-300 border-amber-500/50"
                      : "bg-white/5 hover:bg-white/10 text-slate-300 border-white/10"
                  }`}
                >
                  <span>{ex.region_name}</span>
                  <span className="text-[9px] font-mono text-slate-400 ml-1">({ex.variable_key})</span>
                </button>
              ))}
            </div>
          </div>

          {/* Interactive Chapter Stepper Ribbon */}
          {!isComparing && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
                {CHAPTERS.map((ch) => {
                  const isActive = chapter === ch.num;
                  const isPassed = chapter > ch.num;
                  return (
                    <button
                      key={ch.num}
                      onClick={() => setChapter(ch.num)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 whitespace-nowrap cursor-pointer ${
                        isActive
                          ? "cosmic-gold-button shadow-md scale-105"
                          : isPassed
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          : "bg-white/5 text-slate-400 hover:text-white border border-white/10"
                      }`}
                    >
                      <span
                        className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-mono ${
                          isActive
                            ? "bg-black text-amber-400 font-black"
                            : isPassed
                            ? "bg-amber-400 text-black"
                            : "bg-white/10"
                        }`}
                      >
                        {isPassed ? "✓" : ch.num}
                      </span>
                      <span>{ch.title.split(":")[0]}</span>
                    </button>
                  );
                })}
              </div>

              {/* Scientist View Toggle Pill */}
              <button
                onClick={() => setScientistView((prev) => !prev)}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all flex items-center gap-1.5 border cursor-pointer ${
                  scientistView
                    ? "bg-sky-500/20 text-sky-300 border-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.4)]"
                    : "bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white border-white/10"
                }`}
              >
                <span>🔬</span>
                <span>{scientistView ? "Hide Scientist View" : "Scientist View"}</span>
              </button>
            </div>
          )}
        </header>

        {/* =========================================================================
            COMPARISON MODE BANNER & SECONDARY REGION CONTROLS (IF COMPARING)
            ========================================================================= */}
        {isComparing && (
          <div className="dark-clay-card rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 border border-sky-500/40 bg-sky-950/20">
            <div className="flex items-center gap-3">
              <span className="text-xl">⚖️</span>
              <div>
                <h3 className="text-sm font-bold text-white">Side-by-Side Comparison Mode Active</h3>
                <p className="text-xs text-slate-300 font-mono">
                  Evaluating {v.name} for <strong>{region.name}</strong> vs <strong>{compareRegion.name}</strong>
                </p>
              </div>
            </div>

            {/* Quick Picker for Secondary Region */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Change Region B:</span>
              <select
                value={compareRegion.name}
                onChange={(e) => {
                  const ex = EXAMPLES.find((x) => x.region_name === e.target.value);
                  if (ex) {
                    setCompareRegion({ lat: ex.lat, lon: ex.lon, name: ex.region_name });
                  } else {
                    const c = COUNTRIES.find((x) => x.name === e.target.value);
                    if (c) setCompareRegion({ lat: c.lat, lon: c.lng, name: c.name });
                  }
                }}
                className="bg-[#0a111c] border border-white/20 rounded-xl px-3 py-1.5 text-xs text-white outline-none focus:border-amber-400"
              >
                <optgroup label="NASA Challenge Examples">
                  {EXAMPLES.map((ex) => (
                    <option key={ex.slug} value={ex.region_name}>
                      {ex.region_name} ({ex.country ?? "Demo"})
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Global Regions">
                  {COUNTRIES.slice(0, 15).map((c) => (
                    <option key={c.id} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>
          </div>
        )}

        {/* =========================================================================
            MAIN STAGE + STORY CARDS SPLIT
            ========================================================================= */}
        {isComparing ? (
          /* COMPARATIVE VIEW */
          <div className="flex flex-col gap-4">
            {compareLoading || !compareData ? (
              <div className="dark-clay-card p-12 text-center text-slate-300">
                <Loading text={`Loading comparative satellite records for ${compareRegion.name}...`} />
              </div>
            ) : compareError ? (
              <ErrorBox message={compareError} onRetry={retryCompare} />
            ) : (
              <>
                {/* Comparative KPI Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="dark-clay-card rounded-2xl p-3 border border-white/10">
                    <span className="text-[10px] font-mono text-slate-400 block mb-1">Rate of Change (Slope)</span>
                    <div className="text-xs space-y-1 font-mono">
                      <div className="text-amber-300 font-bold">{data.region.name}: {signed(data.trend.ols.slopePerYear * 10, 3)} {v.unit}/dec</div>
                      <div className="text-sky-300 font-bold">{compareData.region.name}: {signed(compareData.trend.ols.slopePerYear * 10, 3)} {v.unit}/dec</div>
                    </div>
                  </div>

                  <div className="dark-clay-card rounded-2xl p-3 border border-white/10">
                    <span className="text-[10px] font-mono text-slate-400 block mb-1">Statistical Significance</span>
                    <div className="text-xs space-y-1">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${data.trend.verdict === "significant" ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-700 text-slate-300"}`}>
                        {data.region.name}: {data.trend.verdict}
                      </span>
                      <span className={`block px-2 py-0.5 rounded text-[10px] font-bold ${compareData.trend.verdict === "significant" ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-700 text-slate-300"}`}>
                        {compareData.region.name}: {compareData.trend.verdict}
                      </span>
                    </div>
                  </div>

                  <div className="dark-clay-card rounded-2xl p-3 border border-white/10">
                    <span className="text-[10px] font-mono text-slate-400 block mb-1">Total Shift Over Record</span>
                    <div className="text-xs space-y-1 font-mono">
                      <div className="text-amber-300 font-bold">{data.region.name}: {signed(data.trend.totalChange, 2)} {v.unit}</div>
                      <div className="text-sky-300 font-bold">{compareData.region.name}: {signed(compareData.trend.totalChange, 2)} {v.unit}</div>
                    </div>
                  </div>

                  <div className="dark-clay-card rounded-2xl p-3 border border-white/10">
                    <span className="text-[10px] font-mono text-slate-400 block mb-1">Mean Baseline</span>
                    <div className="text-xs space-y-1 font-mono">
                      <div className="text-amber-300 font-bold">{data.region.name}: {fmt(data.trend.mean, 2)} {v.unit}</div>
                      <div className="text-sky-300 font-bold">{compareData.region.name}: {fmt(compareData.trend.mean, 2)} {v.unit}</div>
                    </div>
                  </div>
                </div>

                {/* Comparative Dual Stage */}
                <ComparativeStage dataA={data} dataB={compareData} />

                {/* Comparative Verdict Synthesis */}
                <div className="dark-clay-card rounded-3xl p-5 border border-amber-500/30 flex flex-col gap-2">
                  <h3 className="text-sm font-bold text-amber-300 font-mono uppercase tracking-wider flex items-center gap-2">
                    <span>🔍</span>
                    <span>Comparative Detective Verdict</span>
                  </h3>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    {data.region.name} exhibits a {data.trend.ols.slopePerYear >= 0 ? "warming/rising" : "cooling/decreasing"} rate of{" "}
                    <strong>{signed(data.trend.ols.slopePerYear * 10, 3)} {v.unit}/decade</strong> ({data.trend.verdict === "significant" ? "statistically significant" : "not statistically significant"}), while {compareData.region.name} exhibits a rate of{" "}
                    <strong>{signed(compareData.trend.ols.slopePerYear * 10, 3)} {v.unit}/decade</strong> ({compareData.trend.verdict === "significant" ? "statistically significant" : "not statistically significant"}).
                  </p>
                </div>
              </>
            )}
          </div>
        ) : (
          /* GUIDED 5-CHAPTER STORY MODE */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* LEFT FOCUSED NARRATIVE RAIL (lg:col-span-5) */}
            <div className="lg:col-span-5 flex flex-col justify-between gap-3">
              {/* Active Chapter Story Card */}
              <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-4 sm:p-5 flex flex-col gap-3 shadow-2xl border border-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                    Chapter {chapter} of 5
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {reliabilityPct}% Satellite Completeness
                  </span>
                </div>

                <div>
                  <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                    {CHAPTERS[chapter - 1].title}
                  </h2>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    {CHAPTERS[chapter - 1].subtitle}
                  </p>
                </div>

                {/* Chapter-specific Plain-Language Translation */}
                <div className="text-xs leading-relaxed text-slate-200 pt-2 border-t border-white/10 min-h-[140px] flex flex-col justify-center">
                  {chapter === 1 && (
                    <div className="space-y-2">
                      <p>
                        This is <strong>{region.name}</strong>. Over the satellite era, normal {v.name.toLowerCase()} averages{" "}
                        <strong className="text-amber-300 font-mono">{fmt(normalRange.mean, 1)} {v.unit}</strong>{" "}
                        (with typical readings spanning between {fmt(normalRange.p10, 1)} and {fmt(normalRange.p90, 1)} {v.unit}).
                      </p>
                      <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-[11px] font-mono">
                        <span className="text-slate-400">Data Reliability:</span>
                        <span className="text-emerald-300 font-bold">✓ {reliabilityPct}% Complete Archive</span>
                      </div>
                    </div>
                  )}

                  {chapter === 2 && (
                    <div className="space-y-2">
                      <p>
                        Weather fluctuates naturally. Here, weather stability shows a standard deviation of{" "}
                        <strong className="text-amber-300 font-mono">±{fmt(t.stdDev, 2)} {v.unit}</strong>.
                      </p>
                      <p className="text-slate-300">
                        Pulsing dots highlight extreme peaks and drops. The hottest/highest recorded point was{" "}
                        <strong className="text-amber-300 font-mono">{fmt(normalRange.max, 1)} {v.unit}</strong>{" "}
                        on {t.max.date}, and the lowest was{" "}
                        <strong className="text-sky-300 font-mono">{fmt(normalRange.min, 1)} {v.unit}</strong>{" "}
                        on {t.min.date}.
                      </p>
                    </div>
                  )}

                  {chapter === 3 && (
                    <div className="space-y-2">
                      <p>
                        {isWarmingOrIncrease ? "Rising" : "Declining"} at a rate of{" "}
                        <strong className="text-amber-300 font-mono text-sm">
                          {signed(slopeDecade, 2)} {v.unit}/decade
                        </strong>{" "}
                        (Total change across record: <strong>{signed(t.totalChange, 2)} {v.unit}</strong>).
                      </p>
                      <div
                        className={`p-2.5 rounded-xl border flex items-center justify-between text-[11px] font-mono ${
                          isSignificant
                            ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300 font-bold"
                            : "bg-slate-800/80 border-slate-700 text-slate-300"
                        }`}
                      >
                        <span>Mann-Kendall Test:</span>
                        <span>{isSignificant ? "Mathematically Significant Shift ✅" : "Natural Fluctuation (Not significant yet)"}</span>
                      </div>
                    </div>
                  )}

                  {chapter === 4 && (
                    <div className="space-y-2">
                      <p>
                        Planetary tilt creates a rhythmic 12-month heartbeat. The peak month is{" "}
                        <strong className="text-emerald-300 font-mono">Month {t.seasonalClimatology.indexOf(Math.max(...t.seasonalClimatology)) + 1}</strong>{" "}
                        and the lowest is{" "}
                        <strong className="text-sky-300 font-mono">Month {t.seasonalClimatology.indexOf(Math.min(...t.seasonalClimatology)) + 1}</strong>.
                      </p>
                      <p className="text-slate-300">
                        Our engine subtracts this predictable astronomical wave to expose genuine long-term structural shifts underneath.
                      </p>
                    </div>
                  )}

                  {chapter === 5 && (
                    <div className="space-y-2">
                      <p>
                        Projected outlook from NASA trend model:
                      </p>
                      <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 font-mono text-[11px] space-y-1">
                        <div className="flex justify-between">
                          <span>Horizon:</span>
                          <span className="font-bold">{forecastHorizon} Years ({forecastLoading ? "Fetching API..." : "Live /api/forecast"})</span>
                        </div>
                        {apiForecast?.forecast?.method && (
                          <div className="flex justify-between text-slate-300 text-[10px]">
                            <span>Model Verification:</span>
                            <span>{apiForecast.forecast.method}</span>
                          </div>
                        )}
                        {apiForecast?.forecast?.expectedChange?.absolute !== undefined && (
                          <div className="flex justify-between text-[10px]">
                            <span>Expected Shift from Baseline:</span>
                            <span className="font-bold text-amber-300">{signed(apiForecast.forecast.expectedChange.absolute, 2)} {v.unit}</span>
                          </div>
                        )}
                      </div>

                      {/* Horizon switch */}
                      <div className="flex items-center gap-1.5 pt-1">
                        <span className="text-[10px] text-slate-400">Horizon:</span>
                        {[1, 2, 5, 10].map((h) => (
                          <button
                            key={h}
                            onClick={() => setForecastHorizon(h)}
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                              forecastHorizon === h
                                ? "bg-amber-400 text-black"
                                : "bg-white/10 text-slate-300 hover:text-white"
                            }`}
                          >
                            {h}Y
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Next Step / Action Button */}
                <div className="pt-3 border-t border-white/10 flex items-center justify-between gap-3">
                  {chapter > 1 ? (
                    <button
                      onClick={() => setChapter((prev) => Math.max(1, prev - 1))}
                      className="px-3 py-2 rounded-xl text-xs font-bold text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all cursor-pointer"
                    >
                      ← Previous
                    </button>
                  ) : <div />}

                  {chapter < 5 ? (
                    <button
                      onClick={() => setChapter((prev) => Math.min(5, prev + 1))}
                      className="cosmic-gold-button px-4 py-2 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all shadow-lg active:scale-95 cursor-pointer ml-auto"
                    >
                      <span>{CHAPTERS[chapter - 1].buttonLabel}</span>
                    </button>
                  ) : (
                    <Link
                      href={`/forecast?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(
                        region.name
                      )}&variable=${v.key}&horizon=${forecastHorizon}`}
                      className="cosmic-gold-button px-4 py-2 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer ml-auto"
                    >
                      <span>Full Multi-Year Simulator →</span>
                    </Link>
                  )}
                </div>
              </div>

              {/* AI Assistant Quick Callout */}
              <div className="dark-clay-card rounded-2xl p-3 flex items-center justify-between gap-3 shadow-lg border border-amber-500/20">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg overflow-hidden border border-amber-400/40 bg-black shadow-md shrink-0">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src="/logo.jpg" alt="AI" className="w-full h-full object-contain" />
                  </div>
                  <div className="text-xs">
                    <p className="font-bold text-white">Ask AI Detective</p>
                    <p className="text-[10px] text-slate-400">Suggest variables & interpret {v.name}</p>
                  </div>
                </div>

                <button
                  onClick={() => setIsAssistantOpen(true)}
                  className="cosmic-gold-button px-3 py-1.5 rounded-xl text-xs font-bold active:scale-95 cursor-pointer"
                >
                  Open Assistant
                </button>
              </div>
            </div>

            {/* RIGHT MAIN INTERACTIVE STAGE (lg:col-span-7) */}
            <div className="lg:col-span-7 flex flex-col gap-3">
              <CinematicStage
                chapter={chapter}
                data={data}
                future12Months={future12Months}
                normalRange={normalRange}
              />

              {/* Explainer Subtitle Pill */}
              <div className="dark-clay-card rounded-2xl p-3 flex items-center justify-between text-xs font-mono text-slate-400 shadow-md">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  <span>NASA POWER (MERRA-2 / CERES) 0.5° Grid Analysis</span>
                </div>
                <span className="text-amber-400 font-bold">
                  Step {chapter} / 5 Active
                </span>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            "🔬 SCIENTIST VIEW" COLLAPSIBLE STATISTICAL DRAWER
            ========================================================================= */}
        {scientistView && (
          <section className="dark-clay-card rounded-2xl sm:rounded-3xl p-4 sm:p-5 shadow-2xl border border-sky-500/30 animate-[fadeInUp_0.4s_ease-out]">
            <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
              <div className="flex items-center gap-2">
                <span className="text-base">🔬</span>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                  Scientist View: Rigorous Mathematical Parameters
                </h3>
              </div>
              <span className="text-[11px] font-mono text-sky-400 font-bold">
                Alpha α = 0.05
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                <span className="text-[10px] text-slate-400 block mb-0.5">Sen&apos;s Slope (Yearly):</span>
                <span className="font-black text-amber-300 text-sm">
                  {signed(t.mannKendall.senSlopePerYear, 4)} {v.unit}/yr
                </span>
                <span className="text-[9px] text-slate-500 block mt-0.5">Median of all pairwise slopes</span>
              </div>

              <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                <span className="text-[10px] text-slate-400 block mb-0.5">Mann-Kendall p-value:</span>
                <span className="font-black text-white text-sm">{fmtP(t.mannKendall.pValue)}</span>
                <span className="text-[9px] text-slate-500 block mt-0.5">
                  Tau τ: {t.mannKendall.tau.toFixed(3)} | z: {t.mannKendall.z.toFixed(2)}
                </span>
              </div>

              <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                <span className="text-[10px] text-slate-400 block mb-0.5">Linear OLS Slope:</span>
                <span className="font-black text-white text-sm">
                  {signed(t.ols.slopePerYear, 4)} {v.unit}/yr
                </span>
                <span className="text-[9px] text-slate-500 block mt-0.5">
                  SE: ±{fmt(t.ols.stdErr, 4)} | R²: {t.ols.r2.toFixed(3)}
                </span>
              </div>

              <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                <span className="text-[10px] text-slate-400 block mb-0.5">Serial Autocorrelation (r₁):</span>
                <span className="font-black text-white text-sm">{t.ols.lag1Autocorr.toFixed(3)}</span>
                <span className="text-[9px] text-slate-500 block mt-0.5">
                  Effective N: {Math.round(t.ols.effectiveN)} months
                </span>
              </div>
            </div>

            {/* Descriptive stats table */}
            <div className="mt-3 pt-3 border-t border-white/10 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-300">
              <span>Mean: <strong>{fmt(t.mean, 2)}</strong></span>
              <span>Median: <strong>{fmt(normalRange.median, 2)}</strong></span>
              <span>Std Dev (σ): <strong>{fmt(t.stdDev, 2)}</strong></span>
              <span>Min: <strong>{fmt(normalRange.min, 2)}</strong> ({t.min.date})</span>
              <span>Max: <strong>{fmt(normalRange.max, 2)}</strong> ({t.max.date})</span>
              <span>Span: <strong>{t.period.years} years ({series.length} months)</strong></span>
            </div>
          </section>
        )}

        {/* =========================================================================
            FULL 12 VARIABLES & PERIOD SELECTOR MODAL
            ========================================================================= */}
        {isVariablesModalOpen && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
            <div className="w-full max-w-4xl max-h-[90vh] bg-[#080d16] border border-amber-400/40 rounded-3xl p-5 sm:p-6 flex flex-col gap-4 shadow-2xl overflow-y-auto">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2.5">
                  <span className="text-xl">📊</span>
                  <div>
                    <h2 className="text-lg font-black text-white">All 12 NASA Earth Observation Variables</h2>
                    <p className="text-xs text-slate-400 font-mono">Select any parameter & observation period</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsVariablesModalOpen(false)}
                  className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {/* Time Period Presets */}
              <div className="p-3 rounded-2xl bg-white/5 border border-white/10 flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-mono font-bold text-amber-300">Observation Time Horizon:</span>
                <div className="flex items-center gap-2">
                  {[
                    { label: "5 Years", start: 2019, end: 2024 },
                    { label: "10 Years", start: 2014, end: 2024 },
                    { label: "20 Years", start: 2004, end: 2024 },
                    { label: "Full Archive (1990-2024)", start: 1990, end: 2024 },
                  ].map((p) => {
                    const isActive = sel.start === p.start && sel.end === p.end;
                    return (
                      <button
                        key={p.label}
                        onClick={() => {
                          router.replace(
                            `/dashboard?${selectionToParams({ ...sel, start: p.start, end: p.end })}`
                          );
                        }}
                        className={`px-3 py-1 rounded-xl text-xs font-mono font-bold transition-all ${
                          isActive
                            ? "bg-amber-400 text-black shadow-md"
                            : "bg-white/5 hover:bg-white/15 text-slate-300"
                        }`}
                      >
                        {p.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 12 Variables Grid by Category */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {VARIABLES.map((item) => {
                  const isCurrent = v.key === item.key;
                  return (
                    <button
                      key={item.key}
                      onClick={() => {
                        setIsVariablesModalOpen(false);
                        if (!isCurrent) {
                          router.replace(
                            `/dashboard?${selectionToParams({ ...sel, variable: item.key })}`
                          );
                        }
                      }}
                      className={`p-3.5 rounded-2xl text-left border transition-all flex flex-col justify-between gap-2 group cursor-pointer ${
                        isCurrent
                          ? "bg-amber-500/20 border-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.3)]"
                          : "bg-white/5 hover:bg-white/10 border-white/10 hover:border-amber-400/50"
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between text-xs font-bold text-white group-hover:text-amber-300">
                          <span>{item.name}</span>
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-300">
                            {item.key}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300 mt-1 line-clamp-2 leading-relaxed">
                          {item.definition}
                        </p>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-2 border-t border-white/5">
                        <span>Unit: <strong>{item.unit}</strong></span>
                        <span className="capitalize">{item.category}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Pop-up AI Assistant */}
        {isAssistantOpen && (
          <div className="fixed bottom-6 right-6 z-50 w-84 sm:w-96 max-w-[calc(100vw-3rem)] h-[520px] max-h-[calc(100vh-140px)] flex flex-col pointer-events-auto shadow-2xl">
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

export default function DashboardPageWrapper() {
  return (
    <Suspense
      fallback={
        <PageFrame title="NASA EarthTrend Detective" subtitle="Loading" noScroll={false} theme="clay">
          <Loading text="Preparing Guided Detective Engine..." />
        </PageFrame>
      }
    >
      <DashboardView />
    </Suspense>
  );
}