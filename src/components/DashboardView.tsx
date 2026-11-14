"use client";

import React, { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAsync } from "../lib/useAsync";
import PageFrame, { ErrorBox, Loading } from "./PageFrame";
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
  { key: "T2M", label: "Air Temp", unit: "°C", desc: "Surface Air Temperature (2 meters above ground)" },
  { key: "T2M_MAX", label: "Max Temp", unit: "°C", desc: "Daily Maximum Air Temperature" },
  { key: "PRECTOTCORR", label: "Precipitation", unit: "mm/day", desc: "Rain & Snowfall Precipitation" },
  { key: "GWETROOT", label: "Soil Wetness", unit: "0-1", desc: "Root Zone Soil Moisture Index" },
  { key: "TS", label: "Surface Temp", unit: "°C", desc: "Earth Skin Surface Temperature" },
];

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
    buttonLabel: "What happens next? (1-Year Outlook) →",
  },
  {
    num: 5,
    title: "The Future Horizon & AI Detective",
    subtitle: "1-Year predictive horizon and planetary risk action.",
    buttonLabel: "Explore Multi-Year Scenarios →",
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
          Every screen starts empty until you select a real-world location. We connect directly to NASA satellite archives (POWER, MERRA-2, CERES) to evaluate planetary shifts step-by-step.
        </p>

        {/* Search input */}
        <div className="w-full max-w-md relative mb-6">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search country, territory, or coordinates..."
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
                  )}&variable=T2M&start=1990&end=2025`
                );
              }}
              className="dark-clay-card hover:border-amber-400/50 p-3 rounded-2xl flex flex-col items-start text-left transition-all hover:-translate-y-0.5 group cursor-pointer shadow-md"
            >
              <span className="text-xs font-bold text-white group-hover:text-amber-300 transition-colors">
                {c.name}
              </span>
              <span className="text-[10px] text-slate-400 font-mono mt-0.5">
                {c.region} • {c.lat.toFixed(1)}°, {c.lng.toFixed(1)}°
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
            <span>Fly to 3D Globe to Pick Coordinates</span>
          </Link>

          <Link
            href="/chat"
            className="dark-clay-button px-4 py-2.5 rounded-2xl text-xs font-bold text-slate-300 hover:text-white flex items-center gap-2 transition-all cursor-pointer"
          >
            <div className="w-4 h-4 rounded-full overflow-hidden bg-black shrink-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.jpg" alt="AI" className="w-full h-full object-contain" />
            </div>
            <span>Talk to AI Detective Assistant</span>
          </Link>
        </div>
      </div>
    </PageFrame>
  );
}

// =========================================================================
// MAIN INTERACTIVE STAGE (Animated Canvas with Chapter Morphing)
// =========================================================================
interface StageProps {
  chapter: number;
  data: AnalysisResult;
  future12Months: { x: number; y: number; lower: number; upper: number }[];
  normalRange: { min: number; max: number; mean: number; median: number; p10: number; p90: number };
}

function CinematicStage({
  chapter,
  data,
  future12Months,
  normalRange,
}: StageProps) {
  const { series, trend: t, variable: v } = data;
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const W = 800;
  const H = 340;
  const PAD = { l: 56, r: 24, t: 24, b: 36 };

  // Calculate coordinates bounds
  const xValues = series.map((s) => dateToDecYear(s.date));
  const minX = Math.min(...xValues);
  const maxX = chapter === 5 ? dateToDecYear(series[series.length - 1].date) + 1.05 : Math.max(...xValues);

  const allYValues = [
    ...series.map((s) => s.value),
    normalRange.min,
    normalRange.max,
    ...(chapter === 5 ? future12Months.flatMap((p) => [p.lower, p.upper]) : []),
  ];
  let minY = Math.min(...allYValues);
  let maxY = Math.max(...allYValues);
  const padY = (maxY - minY || 1) * 0.12;
  minY -= padY;
  maxY += padY;

  const sx = (x: number) => PAD.l + ((x - minX) / (maxX - minX || 1)) * (W - PAD.l - PAD.r);
  const sy = (y: number) => H - PAD.b - ((y - minY) / (maxY - minY || 1)) * (H - PAD.t - PAD.b);

  // SVG Line paths
  const historicalPath = series
    .map((s, i) => `${i === 0 ? "M" : "L"}${sx(dateToDecYear(s.date)).toFixed(1)},${sy(s.value).toFixed(1)}`)
    .join(" ");

  const trendLinePath = series
    .map((s, i) => `${i === 0 ? "M" : "L"}${sx(dateToDecYear(s.date)).toFixed(1)},${sy(s.trend).toFixed(1)}`)
    .join(" ");

  // Confidence Interval band for Chapter 3
  const ciMargin = Math.max(0.15, Math.abs(t.ols.stdErr) * 1.96 + t.stdDev * 0.18);
  const ciBandPath =
    series
      .map((s, i) => `${i === 0 ? "M" : "L"}${sx(dateToDecYear(s.date)).toFixed(1)},${sy(s.trend + ciMargin).toFixed(1)}`)
      .join(" ") +
    " " +
    [...series]
      .reverse()
      .map((s) => `L${sx(dateToDecYear(s.date)).toFixed(1)},${sy(s.trend - ciMargin).toFixed(1)}`)
      .join(" ") +
    " Z";

  // Forecast band path for Chapter 5
  const lastPoint = series[series.length - 1];
  const forecastBandPath =
    `M${sx(dateToDecYear(lastPoint.date)).toFixed(1)},${sy(lastPoint.value + 0.3).toFixed(1)} ` +
    future12Months.map((p) => `L${sx(p.x).toFixed(1)},${sy(p.upper).toFixed(1)}`).join(" ") +
    " " +
    [...future12Months].reverse().map((p) => `L${sx(p.x).toFixed(1)},${sy(p.lower).toFixed(1)}`).join(" ") +
    ` L${sx(dateToDecYear(lastPoint.date)).toFixed(1)},${sy(lastPoint.value - 0.3).toFixed(1)} Z`;

  const forecastLinePath =
    `M${sx(dateToDecYear(lastPoint.date)).toFixed(1)},${sy(lastPoint.value).toFixed(1)} ` +
    future12Months.map((p) => `L${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ");

  // Seasonal cycle points for Chapter 4
  const climMean = t.seasonalClimatology.reduce((a, b) => a + b, 0) / 12;
  const seasonalPath = series
    .map((s, i) => {
      const monthIdx = Number(s.date.slice(5, 7)) - 1;
      const seasonalVal = s.trend + (t.seasonalClimatology[monthIdx] - climMean);
      return `${i === 0 ? "M" : "L"}${sx(dateToDecYear(s.date)).toFixed(1)},${sy(seasonalVal).toFixed(1)}`;
    })
    .join(" ");

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
          stroke="#f59e0b"
          strokeWidth="1.2"
          strokeOpacity={chapter === 1 ? "0.8" : "0.25"}
        />

        {chapter === 1 && (
          <g className="animate-[fadeInUp_0.5s_ease-out]">
            <text
              x={W - PAD.r - 8}
              y={sy(normalRange.max) + 14}
              textAnchor="end"
              fill="#38bdf8"
              fontSize="10"
              fontFamily="monospace"
              fontWeight="bold"
            >
              Historical Max: {fmt(normalRange.max, 1)} {v.unit}
            </text>
            <text
              x={W - PAD.r - 8}
              y={sy(normalRange.mean) - 5}
              textAnchor="end"
              fill="#38bdf8"
              fontSize="10"
              fontFamily="monospace"
              fontWeight="bold"
            >
              Historical Mean: {fmt(normalRange.mean, 1)} {v.unit}
            </text>
            <text
              x={W - PAD.r - 8}
              y={sy(normalRange.min) - 6}
              textAnchor="end"
              fill="#38bdf8"
              fontSize="10"
              fontFamily="monospace"
              fontWeight="bold"
            >
              Historical Min: {fmt(normalRange.min, 1)} {v.unit}
            </text>
          </g>
        )}

        {/* -------------------------------------------------------------
            CHAPTER 3: CONFIDENCE INTERVAL BAND & SEN'S SLOPE TRENDLINE
           ------------------------------------------------------------- */}
        {(chapter === 3 || chapter === 5) && (
          <g className="animate-[fadeInUp_0.6s_ease-out]">
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
            CHAPTER 5: 1-YEAR FORECAST EXTENSION & UNCERTAINTY BAND
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
              1-Year Predictive Horizon →
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
          <span className="text-white font-black text-sm">
            {fmt(series[hoverIndex].value, 2)} {v.unit}
          </span>
          <span className="text-amber-400 text-[10px]">
            Δ {signed(series[hoverIndex].anomaly, 2)}
          </span>
        </div>
      )}
    </div>
  );
}

// =========================================================================
// GUIDED DETECTIVE MODE (Main Refactored View)
// =========================================================================
function GuidedDetectiveMode({ data, sel }: { data: AnalysisResult; sel: Selection }) {
  const router = useRouter();
  const [chapter, setChapter] = useState<number>(1);
  const [scientistView, setScientistView] = useState<boolean>(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState<boolean>(false);

  const { trend: t, variable: v, region, series } = data;

  // Calculate descriptive statistics for plain language translation
  const values = useMemo(() => series.map((s) => s.value).sort((a, b) => a - b), [series]);
  const normalRange = useMemo(() => {
    const meanVal = t.mean;
    const medianVal =
      values.length % 2 === 0
        ? (values[values.length / 2 - 1] + values[values.length / 2]) / 2
        : values[Math.floor(values.length / 2)];
    const p10 = values[Math.floor(values.length * 0.1)] ?? values[0];
    const p90 = values[Math.floor(values.length * 0.9)] ?? values[values.length - 1];

    return {
      min: t.min.value,
      max: t.max.value,
      mean: meanVal,
      median: medianVal,
      p10,
      p90,
    };
  }, [t, values]);

  // Decadal slope & statistical verdict
  const slopeDecade = t.ols.slopePerYear * 10;
  const isWarmingOrIncrease = t.ols.slopePerYear > 0;
  const isSignificant = t.verdict === "significant";

  // Data completeness badge
  const expectedMonths = t.period.months || series.length;
  const reliabilityPct = Math.min(100, Math.round((series.length / expectedMonths) * 100));

  // 1-Year Forecast calculations for Chapter 5
  const lastPoint = series[series.length - 1];
  const lastDate = lastPoint?.date ?? `${t.period.end}-12`;
  const lastYear = Number(lastDate.slice(0, 4));
  const lastMonth = Number(lastDate.slice(5, 7));

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

  // Country Object for AI Assistant
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
                    NASA Detective Mode
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

            {/* Quick Variable Switcher + 3D Globe Link */}
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
                        ? "bg-amber-500 text-black border-amber-300 font-bold shadow-md shadow-amber-900/40"
                        : "dark-clay-button text-slate-300 hover:text-white"
                    }`}
                  >
                    {qv.label}
                  </button>
                );
              })}

              <Link
                href={`/?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(region.name)}`}
                className="dark-clay-button px-3 py-1 rounded-xl text-xs font-bold text-amber-300 hover:text-white flex items-center gap-1.5 transition-all ml-1 border border-amber-500/30"
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

          {/* Interactive Chapter Stepper Ribbon */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
              {CHAPTERS.map((ch) => {
                const isActive = chapter === ch.num;
                const isPassed = chapter > ch.num;
                return (
                  <button
                    key={ch.num}
                    onClick={() => setChapter(ch.num)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border cursor-pointer ${
                      isActive
                        ? "bg-amber-500 text-black border-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.4)]"
                        : isPassed
                        ? "bg-amber-950/40 text-amber-300 border-amber-500/30 hover:border-amber-400"
                        : "dark-clay-button text-slate-400 hover:text-white"
                    }`}
                  >
                    <span
                      className={`w-4 h-4 rounded-full text-[10px] flex items-center justify-center font-mono font-black ${
                        isActive
                          ? "bg-black text-amber-400"
                          : isPassed
                          ? "bg-amber-500 text-black"
                          : "bg-white/10 text-slate-300"
                      }`}
                    >
                      {ch.num}
                    </span>
                    <span className="hidden md:inline whitespace-nowrap">{ch.title}</span>
                  </button>
                );
              })}
            </div>

            {/* Toggle Scientist View Button */}
            <button
              onClick={() => setScientistView((prev) => !prev)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 border cursor-pointer ${
                scientistView
                  ? "bg-sky-500 text-black border-sky-300 shadow-md shadow-sky-900/40"
                  : "dark-clay-button text-slate-300 hover:text-white border-white/15"
              }`}
            >
              <span>🔬</span>
              <span>{scientistView ? "Hide Scientist View" : "Scientist View"}</span>
            </button>
          </div>
        </header>

        {/* =========================================================================
            STAGE + STORY SPLIT (Cinematic Canvas + Focused Story Card)
            ========================================================================= */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* LEFT NARRATIVE STORY CARD (lg:col-span-5) */}
          <div className="lg:col-span-5 flex flex-col gap-3">
            <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-4 sm:p-5 flex flex-col justify-between shadow-xl border border-white/10 min-h-[360px]">
              {/* Chapter Header */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
                    Chapter {chapter} of 5
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    NASA POWER • {series.length} Months
                  </span>
                </div>

                <h2 className="text-xl font-black text-white tracking-tight mb-1">
                  {CHAPTERS[chapter - 1].title}
                </h2>
                <p className="text-xs font-medium text-amber-300/90 mb-4">
                  {CHAPTERS[chapter - 1].subtitle}
                </p>

                {/* Plain Human Language Story Content for Each Chapter */}
                {chapter === 1 && (
                  <div className="space-y-3 text-xs text-slate-300 leading-relaxed animate-[fadeInUp_0.3s_ease-out]">
                    <p>
                      Before deciding if the climate is changing, detectives first establish{" "}
                      <strong className="text-white">what &quot;normal&quot; looks like</strong>.
                    </p>
                    <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Data Reliability:</span>
                        <span className="font-bold text-emerald-400 font-mono">
                          {reliabilityPct}% Complete ({series.length} / {expectedMonths} mos)
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Baseline Normal Mean:</span>
                        <span className="font-bold text-white font-mono">
                          {fmt(normalRange.mean, 1)} {v.unit}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Historical Extremes:</span>
                        <span className="font-bold text-white font-mono">
                          {fmt(normalRange.min, 1)} to {fmt(normalRange.max, 1)} {v.unit}
                        </span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      The shaded band on the stage marks the typical seasonal envelope. Next, let&apos;s watch how year-to-year weather danced across this range.
                    </p>
                  </div>
                )}

                {chapter === 2 && (
                  <div className="space-y-3 text-xs text-slate-300 leading-relaxed animate-[fadeInUp_0.3s_ease-out]">
                    <p>
                      Weather is naturally bouncy. Planetary detectives evaluate{" "}
                      <strong className="text-white">weather stability</strong>: does this region experience calm seasons or wild swings?
                    </p>
                    <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Weather Stability:</span>
                        <span className="font-bold text-amber-400">
                          {t.stdDev / (Math.abs(t.mean) || 1) < 0.15 ? "High (Steady)" : "Dynamic Swings"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Standard Deviation (Spread):</span>
                        <span className="font-bold text-white font-mono">
                          ±{fmt(t.stdDev, 2)} {v.unit}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Extreme Events (P10 / P90):</span>
                        <span className="font-bold text-sky-400 font-mono">
                          {fmt(normalRange.p10, 1)} / {fmt(normalRange.p90, 1)} {v.unit}
                        </span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Pulsing circles on the chart spotlight anomalous peaks and dips. But are these swings random weather noise or a permanent drift?
                    </p>
                  </div>
                )}

                {chapter === 3 && (
                  <div className="space-y-3 text-xs text-slate-300 leading-relaxed animate-[fadeInUp_0.3s_ease-out]">
                    <p>
                      Here is the core answer to NASA&apos;s detective challenge:{" "}
                      <strong className="text-white">What is changing, and is it statistically proven?</strong>
                    </p>
                    <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Verdict:</span>
                        <span
                          className={`font-black font-mono px-2 py-0.5 rounded text-[11px] ${
                            isSignificant
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                              : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          }`}
                        >
                          {isSignificant ? "Statistically Proven Trend" : "Natural Baseline Noise"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Decadal Speed:</span>
                        <span className="font-bold text-amber-400 font-mono text-sm">
                          {signed(slopeDecade, 2)} {v.unit} / decade
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Total Measured Shift:</span>
                        <span className="font-bold text-white font-mono">
                          {signed(t.totalChange, 1)} {v.unit} over {t.period.years} years
                        </span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      {isSignificant
                        ? "Confidence > 95%: This shift exceeds natural climate noise and will continue to alter local environmental balances."
                        : "Variations remain within historical random noise boundaries."}
                    </p>
                  </div>
                )}

                {chapter === 4 && (
                  <div className="space-y-3 text-xs text-slate-300 leading-relaxed animate-[fadeInUp_0.3s_ease-out]">
                    <p>
                      Every location has an annual <strong className="text-white">seasonal heartbeat</strong>.
                      Scientists use seasonal decomposition to isolate genuine long-term changes from regular summer warmth and winter chill.
                    </p>
                    <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Annual Heartbeat Cycle:</span>
                        <span className="font-bold text-emerald-400 font-mono">
                          12-Month Harmonic Wave
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Warmest Month Climatology:</span>
                        <span className="font-bold text-white font-mono">
                          {fmt(Math.max(...t.seasonalClimatology), 1)} {v.unit}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Coolest Month Climatology:</span>
                        <span className="font-bold text-white font-mono">
                          {fmt(Math.min(...t.seasonalClimatology), 1)} {v.unit}
                        </span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      The green curve traces the regular repeating cycle. Now, what does science predict for the immediate future?
                    </p>
                  </div>
                )}

                {chapter === 5 && (
                  <div className="space-y-3 text-xs text-slate-300 leading-relaxed animate-[fadeInUp_0.3s_ease-out]">
                    <p>
                      Forecasting extends the trend into the forward horizon. Planetary detectives use this projection to protect agriculture, infrastructure, and water resources.
                    </p>
                    <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Projected 1-Year Baseline:</span>
                        <span className="font-bold text-amber-400 font-mono text-sm">
                          {fmt(projectedNextYearMean, 1)} {v.unit}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Uncertainty Envelope:</span>
                        <span className="font-bold text-white font-mono">
                          ±{fmt(forecastMargin, 1)} {v.unit} (95% CI)
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Future Trend Direction:</span>
                        <span className="font-bold text-white">
                          {isWarmingOrIncrease ? "Upward Accumulation" : "Downward Drift"}
                        </span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Ready to ask questions or simulate 5-year and 10-year scenarios? Launch the AI Detective Assistant below.
                    </p>
                  </div>
                )}
              </div>

              {/* Action Buttons: Next / Previous */}
              <div className="mt-5 pt-3 border-t border-white/10 flex items-center justify-between gap-2">
                {chapter > 1 ? (
                  <button
                    onClick={() => setChapter((c) => c - 1)}
                    className="dark-clay-button px-3 py-2 rounded-xl text-xs font-bold text-slate-300 hover:text-white transition-all cursor-pointer"
                  >
                    ← Previous
                  </button>
                ) : (
                  <div />
                )}

                {chapter < 5 ? (
                  <button
                    onClick={() => setChapter((c) => c + 1)}
                    className="cosmic-gold-button px-4 py-2 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer"
                  >
                    <span>{CHAPTERS[chapter - 1].buttonLabel}</span>
                  </button>
                ) : (
                  <Link
                    href={`/forecast?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(
                      region.name
                    )}&variable=${v.key}&horizon=5`}
                    className="cosmic-gold-button px-4 py-2 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer"
                  >
                    <span>Simulate 5-Year Scenarios →</span>
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
                  <p className="text-[10px] text-slate-400">Query trends, causes & NASA missions</p>
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

        {/* Floating AI Assistant Modal */}
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

// =========================================================================
// DATA FETCHER (Wraps API call with loading and error boundaries)
// =========================================================================
function DashboardDataContainer({ sel }: { sel: Selection }) {
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

  return <GuidedDetectiveMode data={data} sel={sel} />;
}

// =========================================================================
// INNER CLIENT COMPONENT (Consumes useSearchParams inside Suspense)
// =========================================================================
function DashboardInner() {
  const sp = useSearchParams();
  const sel = parseSelection(sp);

  // If no location parameters are specified in the URL, render the Target Discovery Launcher (Zero fake data)
  if (!sel) {
    return <TargetDiscoveryLauncher />;
  }

  return <DashboardDataContainer sel={sel} />;
}

export default function DashboardView() {
  return (
    <Suspense
      fallback={
        <PageFrame title="NASA EarthTrend Detective" subtitle="Loading" noScroll={false} theme="clay">
          <Loading text="Loading NASA Satellite Records..." />
        </PageFrame>
      }
    >
      <DashboardInner />
    </Suspense>
  );
}
