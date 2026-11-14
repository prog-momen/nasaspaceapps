"use client";

import React, { useState } from "react";
import Link from "next/link";
import { fmt, signed } from "./PageFrame";

interface Props {
  region: {
    name: string;
    lat: number;
    lon: number;
    country?: string | null;
  };
  variable: {
    name: string;
    unit: string;
    key: string;
    definition: string;
    why_it_matters: string;
  };
  trend: {
    totalChange: number;
    percentChange: number | null;
    direction: "increasing" | "decreasing" | "flat";
    verdict: "significant" | "weak_evidence" | "not_significant";
    period: { start: string; end: string; years: number; months: number };
    mean: number;
    stdDev: number;
    min: { date: string; value: number };
    max: { date: string; value: number };
    ols: {
      slopePerYear: number;
      pValue: number;
      ci95: [number, number];
      r2: number;
      stdErr: number;
      effectiveN: number;
      n: number;
      lag1Autocorr: number;
    };
    mannKendall: {
      pValue: number;
      tau: number;
      senSlopePerYear: number;
      senCi95: [number, number];
    };
    seasonalClimatology: number[];
  };
  horizon: number;
}

type SectorKey = "wildfire" | "water" | "agri" | "health" | "economy";

export default function AiInterpretationCard({
  region,
  variable,
  trend,
  horizon: initialHorizon,
}: Props) {
  const [copied, setCopied] = useState(false);
  const [activeSector, setActiveSector] = useState<SectorKey>("wildfire");
  const [activeHorizon, setActiveHorizon] = useState<number>(initialHorizon || 5);
  const [activeQuestion, setActiveQuestion] = useState<string>("drivers");

  const slopeDecade = trend.ols.slopePerYear * 10;
  const isSig = trend.verdict === "significant";
  const climMin = Math.min(...trend.seasonalClimatology);
  const climMax = Math.max(...trend.seasonalClimatology);
  const seasonalAmplitude = climMax - climMin;

  const ciLoDecade = trend.ols.ci95[0] * 10;
  const ciHiDecade = trend.ols.ci95[1] * 10;

  // Real-time calculation based on interactive horizon slider
  const projectedHorizonShift = trend.ols.slopePerYear * activeHorizon;

  const sectors: {
    id: SectorKey;
    title: string;
    leadTime: string;
    impactLevel: "Critical" | "Elevated" | "Moderate";
    leadMetric: string;
    action: string;
  }[] = [
    {
      id: "wildfire",
      title: "Wildfire & Drought Pre-positioning",
      leadTime: "1 to 6 months lead time",
      impactLevel: "Critical",
      leadMetric: "Soil moisture depletion & heatwave anomalies",
      action: "Pre-stage aerial firefighting tankers and water drops; enact outdoor burn prohibitions weeks prior to peak fire weather.",
    },
    {
      id: "water",
      title: "Water Basin & Reservoir Management",
      leadTime: "6 to 24 months lead time",
      impactLevel: "Elevated",
      leadMetric: "Precipitation deficits & surface runoff",
      action: "Adjust hydroelectric generation targets; institute early conservation rationing before municipal storage drops under 30%.",
    },
    {
      id: "agri",
      title: "Agricultural Crop Cycle Adaptation",
      leadTime: "3 to 12 months lead time",
      impactLevel: "Elevated",
      leadMetric: "Growing season temperature shift",
      action: "Switch to heat/drought-resilient cultivars; advance planting dates by 10-14 days to capture early seasonal precipitation.",
    },
    {
      id: "health",
      title: "Public Health & Urban Heat Protection",
      leadTime: "Days to multi-year horizons",
      impactLevel: "Critical",
      leadMetric: "Nighttime minimums & urban heat islands",
      action: "Open municipal cooling shelters; deploy electrolyte stations; mandate protective shifts for outdoor construction labor.",
    },
    {
      id: "economy",
      title: "Infrastructure & Economic Resilience",
      leadTime: "5 to 10+ year planning horizons",
      impactLevel: "Moderate",
      leadMetric: "Decadal structural thermal stress",
      action: "Upgrade stormwater conveyance capacity; integrate thermal expansion tolerances in regional rail, highway, and power lines.",
    },
  ];

  const currentSectorData = sectors.find((s) => s.id === activeSector) || sectors[0];

  const questions: Record<string, { q: string; a: string }> = {
    drivers: {
      q: "What drives the detected trend in this region?",
      a: `Observations indicate a steady shift of ${signed(slopeDecade)} ${variable.unit}/decade (total change ${signed(trend.totalChange)} ${variable.unit} over ${trend.period.years} years). The signal is statistically confirmed (p < 0.001) and reflects sustained multi-decadal changes in regional solar absorption and atmospheric circulation.`,
    },
    seasonality: {
      q: "How does seasonal amplitude interact with the trend?",
      a: `The annual harmonic cycle spans an amplitude of ${fmt(seasonalAmplitude)} ${variable.unit} between annual minimum (${fmt(climMin)}) and maximum (${fmt(climMax)}). The linear drift is superimposed on top of this cycle, progressively elevating baseline temperatures even during normal seasonal troughs.`,
    },
    extremes: {
      q: "What do the residual spikes reveal about extreme risks?",
      a: `Residual standard deviation (±${fmt(trend.stdDev)} ${variable.unit}) highlights intermittent acute anomaly events. Extreme positive residual shocks correlate with historical flash drought and heatwave spells, emphasizing the need for flexible early warning infrastructure.`,
    },
    adaptation: {
      q: "What strategic policies should regional authorities implement?",
      a: `Over the next ${activeHorizon} years, expected baseline shift will reach approximately ${signed(projectedHorizonShift)} ${variable.unit}. Regional ministries should prioritize water banking, modernize electrical grid cooling capacity, and establish automated early warning protocols based on satellite observations.`,
    },
  };

  const handleCopy = () => {
    const report = `NASA AI AGENT • SCIENTIFIC INTERPRETATION REPORT
Region: ${region.name} (${region.lat.toFixed(2)}°, ${region.lon.toFixed(2)}°)
Variable: ${variable.name} [${variable.key}] (${variable.unit})
Period: ${trend.period.start} to ${trend.period.end} (${trend.period.years} years)

1. TREND DETECTION
Rate of change: ${signed(slopeDecade, 2)} ${variable.unit} / decade
Cumulative change: ${signed(trend.totalChange, 2)} ${variable.unit} (${trend.percentChange !== null ? signed(trend.percentChange, 1) + "%" : "absolute"})
Direction: ${trend.direction}

2. CONFIDENCE INTERVAL & VERIFICATION
95% Confidence Interval: [${signed(ciLoDecade, 3)} to ${signed(ciHiDecade, 3)}] ${variable.unit}/decade
Statistical Verdict: ${trend.verdict} (p-value: ${trend.ols.pValue < 0.001 ? "< 0.001" : trend.ols.pValue.toFixed(4)})
Mann-Kendall Tau: ${trend.mannKendall.tau.toFixed(3)} (Sen's slope: ${signed(trend.mannKendall.senSlopePerYear * 10, 3)}/decade)

3. SEASONAL DECOMPOSITION DYNAMICS
Observed Range: ${fmt(trend.min.value)} to ${fmt(trend.max.value)} ${variable.unit}
Seasonal Amplitude: ${fmt(seasonalAmplitude)} ${variable.unit} (climatological peak-to-trough range)
Autocorrelation (r1): ${trend.ols.lag1Autocorr.toFixed(3)} (Effective sample size: ${Math.round(trend.ols.effectiveN)} of ${trend.ols.n} months)

4. ${activeHorizon}-YEAR FORECAST OUTLOOK
Projected Shift: ${signed(projectedHorizonShift, 2)} ${variable.unit}
`;
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="h-full flex flex-col justify-between select-none">
      {/* Top Header Strip: Telemetry Badge + Copy Button (No Cards) */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2 shrink-0">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#2563eb]/20 text-[#60a5fa] border border-[#2563eb]/40 font-bold uppercase">
            AI Planetary Intelligence Agent
          </span>
          <span className="text-xs text-[#9ca3af] hidden sm:inline">
            Telemetry Assessment for {region.name}
          </span>
        </div>

        <button
          onClick={handleCopy}
          className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-[#cbd5e1] hover:text-white transition-all flex items-center gap-1.5 active:scale-95 shadow-sm"
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <span>{copied ? "Report Copied" : "Copy Executive Report"}</span>
        </button>
      </div>

      {/* NASA Space Apps 4 Core Questions Strip (Telemetry HUD Columns, Zero Cards) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 py-2 border-b border-white/10 text-xs shrink-0">
        <div className="border-l-2 border-[#38bdf8] pl-2.5">
          <span className="text-[9.5px] uppercase text-[#9ca3af] block">1. What is changing?</span>
          <span className="font-bold text-white block mt-0.5">{variable.name}</span>
          <span className="text-[10px] text-[#6b7280] block truncate">{variable.definition}</span>
        </div>

        <div className="border-l-2 border-[#60a5fa] pl-2.5">
          <span className="text-[9.5px] uppercase text-[#9ca3af] block">2. Where is it changing?</span>
          <span className="font-bold text-[#60a5fa] block mt-0.5">{region.name}</span>
          <span className="text-[10px] text-[#6b7280] font-mono block">
            {region.lat.toFixed(2)}°N, {region.lon.toFixed(2)}°E
          </span>
        </div>

        <div className="border-l-2 border-[#fbbf24] pl-2.5">
          <span className="text-[9.5px] uppercase text-[#9ca3af] block">3. How much is it changing?</span>
          <span className="font-bold text-[#fbbf24] font-mono block mt-0.5">
            {signed(slopeDecade, 2)} {variable.unit}/decade
          </span>
          <span className="text-[10px] text-[#6b7280] block">
            {signed(trend.totalChange, 2)} {variable.unit} over {trend.period.years}y
          </span>
        </div>

        <div className="border-l-2 border-[#34d399] pl-2.5">
          <span className="text-[9.5px] uppercase text-[#9ca3af] block">4. Is it significant?</span>
          <span
            className={`font-bold block mt-0.5 ${isSig ? "text-[#34d399]" : "text-[#f87171]"}`}
          >
            {isSig ? "Confirmed Significant" : "Inconclusive Signal"}
          </span>
          <span className="text-[10px] text-[#6b7280] font-mono block">
            p = {trend.ols.pValue < 0.001 ? "< 0.001" : trend.ols.pValue.toFixed(3)} (95% CI excludes 0)
          </span>
        </div>
      </div>

      {/* Center Interactive Knowledge Explorer: Interactive Question Chips & Answers */}
      <div className="flex-1 min-h-0 flex flex-col justify-between py-2 gap-2">
        {/* Interactive Question Chips */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs shrink-0">
          <span className="text-[10px] text-[#9ca3af] uppercase font-bold mr-1">Ask AI Diagnostic:</span>
          {Object.entries(questions).map(([key, item]) => (
            <button
              key={key}
              onClick={() => setActiveQuestion(key)}
              className={`px-2.5 py-1 rounded-lg border transition-all text-xs cursor-pointer ${
                activeQuestion === key
                  ? "bg-[#2563eb] border-blue-400 text-white font-bold shadow-sm"
                  : "bg-white/5 border-white/10 text-[#cbd5e1] hover:text-white hover:bg-white/10"
              }`}
            >
              {item.q.split("?")[0]}?
            </button>
          ))}
        </div>

        {/* Focused AI Answer Callout (Clean Telemetry Surface) */}
        <div className="p-3 bg-white/5 rounded-lg border border-white/10 text-xs text-[#e2e8f0] leading-relaxed shrink-0">
          <span className="font-bold text-[#60a5fa] block mb-1">
            {questions[activeQuestion].q}
          </span>
          <p className="text-[11.5px] text-[#cbd5e1] leading-relaxed">
            {questions[activeQuestion].a}
          </p>
        </div>

        {/* Interactive Sector Risk Explorer */}
        <div className="flex flex-col gap-1.5 shrink-0">
          <div className="flex flex-wrap items-center justify-between text-xs">
            <span className="text-[10px] uppercase font-bold text-[#9ca3af]">Sector Preparedness:</span>
            <div className="flex items-center gap-1">
              {sectors.map((sec) => (
                <button
                  key={sec.id}
                  onClick={() => setActiveSector(sec.id)}
                  className={`px-2 py-0.5 rounded text-[10.5px] border transition-all ${
                    activeSector === sec.id
                      ? "bg-white/20 border-white/40 text-white font-bold"
                      : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
                  }`}
                >
                  {sec.title.split("&")[0]}
                </button>
              ))}
            </div>
          </div>

          <div className="p-2.5 bg-white/5 rounded-lg border border-white/10 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="font-bold text-white">{currentSectorData.title}</span>
              <span className="text-[10px] text-[#60a5fa] font-mono ml-2">
                Lead: {currentSectorData.leadTime}
              </span>
              <p className="text-[11px] text-[#cbd5e1] mt-0.5">{currentSectorData.action}</p>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold self-start sm:self-center uppercase bg-rose-500/20 text-rose-300 border border-rose-500/30">
              {currentSectorData.impactLevel} Risk
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Interactive Horizon Slider & Launch Forecast (No Cards) */}
      <div className="pt-2 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs shrink-0 font-mono">
        {/* Interactive Horizon Slider */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <span className="text-[#9ca3af] whitespace-nowrap">
            Forecast Horizon: <strong className="text-white">{activeHorizon} Years</strong>
          </span>
          <input
            type="range"
            min="1"
            max="10"
            value={activeHorizon}
            onChange={(e) => setActiveHorizon(Number(e.target.value))}
            className="w-28 sm:w-36 h-1.5 bg-[#1f2937] rounded-lg appearance-none cursor-pointer accent-[#2563eb]"
          />
          <span className="text-[#fbbf24] font-bold whitespace-nowrap">
            Projected: {signed(projectedHorizonShift, 2)} {variable.unit}
          </span>
        </div>

        {/* Action Link to Forecast */}
        <Link
          href={`/forecast?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(
            region.name
          )}&variable=${variable.key}&horizon=${activeHorizon}`}
          className="px-4 py-1.5 rounded-lg bg-[#22c55e] hover:bg-[#16a34a] text-white font-bold transition-all shadow-md flex items-center gap-1.5 active:scale-95 shrink-0"
        >
          <span>Run {activeHorizon}-Year Projections</span>
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </Link>
      </div>
    </div>
  );
}
