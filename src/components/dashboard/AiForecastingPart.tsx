"use client";

import React, { useState } from "react";
import Link from "next/link";
import { fmt, signed } from "../PageFrame";

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

export default function AiForecastingPart({
  region,
  variable,
  trend,
  horizon: initialHorizon,
}: Props) {
  const [activeSector, setActiveSector] = useState<SectorKey>("wildfire");
  const [activeHorizon, setActiveHorizon] = useState<number>(initialHorizon || 5);

  const slopeDecade = trend.ols.slopePerYear * 10;
  const isSig = trend.verdict === "significant";
  const climMin = Math.min(...trend.seasonalClimatology);
  const climMax = Math.max(...trend.seasonalClimatology);

  const ciLoDecade = trend.ols.ci95[0] * 10;
  const ciHiDecade = trend.ols.ci95[1] * 10;

  // Real-time calculation based on interactive horizon slider
  const projectedHorizonShift = trend.ols.slopePerYear * activeHorizon;

  const sectors: {
    id: SectorKey;
    title: string;
    leadTime: string;
    decisionWindow: string;
    summary: string;
    actions: string[];
    benefit: string;
  }[] = [
    {
      id: "wildfire",
      title: "Wildfire & Heat Preparedness",
      leadTime: "1 to 3 months",
      decisionWindow: "Pre-season resource staging & dry-season bans",
      summary: `Thermal anomalies of ${signed(slopeDecade, 2)} ${variable.unit}/decade accelerate fuel desiccation. Annual climatology ranges from ${fmt(climMin, 1)} to ${fmt(climMax, 1)} ${variable.unit}.`,
      actions: [
        "Position aerial firefighting assets prior to dry seasonal onset",
        "Enforce agricultural burn moratoria when residuals spike > 1.5σ",
        "Implement urban cooling centers in heat-vulnerable sectors",
      ],
      benefit: "Reduces emergency response mobilization costs by 35% and safeguards high-risk population zones.",
    },
    {
      id: "water",
      title: "Water Reservoir & Runoff Management",
      leadTime: "3 to 6 months",
      decisionWindow: "Winter snowpack & spring melt reservoir balancing",
      summary: `Decadal drift of ${signed(slopeDecade, 2)} ${variable.unit}/decade shifts annual melt timing and reservoir recharge schedules.`,
      actions: [
        "Adjust rule curves for multi-purpose flood/storage dams",
        "Pre-release reservoir storage ahead of predicted precipitation surges",
        "Buffer groundwater extraction limits during forecasted droughts",
      ],
      benefit: "Prevents dam overspill flooding and guarantees dry-season municipal water supply security.",
    },
    {
      id: "agri",
      title: "Agricultural Planting & Crop Security",
      leadTime: "2 to 4 months",
      decisionWindow: "Seed cultivar selection & irrigation scheduling",
      summary: `Crop growing degree days shift by ${signed(slopeDecade, 2)} ${variable.unit}/decade, modifying optimal sowing windows.`,
      actions: [
        "Select drought-tolerant or heat-resistant crop varieties",
        "Optimize nitrogen fertilization timing to avoid runoff losses",
        "Schedule precision irrigation matching projected soil moisture deficits",
      ],
      benefit: "Protects regional yields against heat shocks and reduces unnecessary irrigation power draw.",
    },
    {
      id: "health",
      title: "Public Health & Heat Morbidity",
      leadTime: "2 to 8 weeks",
      decisionWindow: "Hospital surge staffing & power grid readiness",
      summary: `Extreme summer temperatures are trending upward by ${signed(slopeDecade, 2)} ${variable.unit}/decade.`,
      actions: [
        "Issue targeted biometric heat stress alerts to elderly care networks",
        "Stock hospital emergency reserves with dehydration therapies",
        "Coordinate grid peak-load shaving with high industrial consumers",
      ],
      benefit: "Lowers heat-related excess mortality and eliminates blackout risks during extreme heatwaves.",
    },
    {
      id: "economy",
      title: "Municipal Infrastructure & Supply Chains",
      leadTime: "1 to 5 years",
      decisionWindow: "Capital budget planning & road/rail resilience",
      summary: `Projected ${activeHorizon}-year shift of ${signed(projectedHorizonShift, 2)} ${variable.unit} impacts infrastructure lifespans.`,
      actions: [
        "Upgrade asphalt binder grades to resist thermal rutting",
        "Re-evaluate flood drainage return-period engineering specs",
        "Hedge energy commodity contracts against prolonged thermal deviations",
      ],
      benefit: "Avoids premature structural degradation and secures supply-chain continuity.",
    },
  ];

  const currentSector = sectors.find((s) => s.id === activeSector) || sectors[0];

  return (
    <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 h-full flex flex-col justify-between gap-2.5 select-none text-slate-100 font-sans">
      {/* 1. TOP HEADER & NASA CHALLENGE 4-QUESTION SYNTHESIS */}
      <div className="flex flex-col gap-2 pb-2 border-b border-white/10 shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase">
              Part 4: AI Environmental Intelligence & Predictive Impact
            </span>
            <span className="text-xs text-slate-400 hidden sm:inline">
              NASA Space Apps 2026 Core Questions & Societal Action
            </span>
          </div>
          <span className="text-xs font-bold text-slate-300 bg-white/5 px-2.5 py-0.5 rounded-full border border-white/10">
            {region.name} • {trend.period.years}Y Observation
          </span>
        </div>

        {/* 4 Core NASA Challenge Diagnostic Panels */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
          {/* Question 1: What */}
          <div className="dark-clay-inset rounded-xl p-2 sm:p-2.5 border border-sky-500/20">
            <span className="text-[10px] uppercase font-bold text-sky-400 block">1. What is Changing?</span>
            <span className="text-sm font-bold text-white mt-0.5 block truncate">{variable.name}</span>
            <span className="text-[10px] text-slate-400 block truncate">
              {trend.direction === "increasing" ? "Upward warming drift" : trend.direction === "decreasing" ? "Downward cooling drift" : "Stationary baseline"}
            </span>
          </div>

          {/* Question 2: Where */}
          <div className="dark-clay-inset rounded-xl p-2 sm:p-2.5 border border-emerald-500/20">
            <span className="text-[10px] uppercase font-bold text-emerald-400 block">2. Where is it Occurring?</span>
            <span className="text-sm font-bold text-white mt-0.5 block truncate">{region.name}</span>
            <span className="text-[10px] text-slate-400 block font-mono truncate">
              {region.lat.toFixed(2)}°N, {region.lon.toFixed(2)}°E
            </span>
          </div>

          {/* Question 3: How Much */}
          <div className="dark-clay-inset rounded-xl p-2 sm:p-2.5 border border-amber-500/20">
            <span className="text-[10px] uppercase font-bold text-amber-400 block">3. How Much Change?</span>
            <span className="text-sm font-mono font-bold text-white mt-0.5 block truncate">
              {signed(slopeDecade, 2)} {variable.unit}/dec
            </span>
            <span className="text-[10px] text-slate-400 block font-mono truncate">
              Total {signed(trend.totalChange, 2)} {variable.unit} ({trend.period.years}y)
            </span>
          </div>

          {/* Question 4: Is it Significant */}
          <div className="dark-clay-inset rounded-xl p-2 sm:p-2.5 border border-purple-500/20">
            <span className="text-[10px] uppercase font-bold text-purple-400 block">4. Is it Significant?</span>
            <span className="text-sm font-bold text-white mt-0.5 block truncate">
              {isSig ? "Yes (p < 0.05)" : "Inconclusive"}
            </span>
            <span className="text-[10px] text-slate-400 block font-mono truncate">
              CI95: [{signed(ciLoDecade, 2)}, {signed(ciHiDecade, 2)}]
            </span>
          </div>
        </div>
      </div>

      {/* 2. CENTER SECTION: 5 STRATEGIC BENEFITS OF FORECASTING */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 flex-1 min-h-0">
        {/* Left: Sector Selector Tabs */}
        <div className="dark-clay-card-sm rounded-2xl p-2.5 sm:p-3 flex flex-col justify-between">
          <div>
            <h4 className="text-xs font-bold text-white mb-1.5 pb-1 border-b border-white/10">
              5 Strategic Benefits of Climate Forecasting
            </h4>
            <div className="flex flex-col gap-1.5">
              {sectors.map((s) => {
                const isActive = s.id === activeSector;
                return (
                  <button
                    key={s.id}
                    onClick={() => setActiveSector(s.id)}
                    className={`p-2 rounded-xl text-left transition-all flex items-center justify-between border ${
                      isActive
                        ? "bg-sky-500 text-white font-bold border-sky-400 shadow-md shadow-sky-900/40"
                        : "dark-clay-button text-slate-300"
                    }`}
                  >
                    <div>
                      <span className="text-xs block">{s.title}</span>
                      <span className={`text-[9.5px] ${isActive ? "text-sky-100" : "text-slate-400"}`}>
                        Lead Time: {s.leadTime}
                      </span>
                    </div>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className={isActive ? "text-white" : "text-slate-400"}>
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </button>
                );
              })}
            </div>
          </div>
          <p className="text-[9.5px] text-slate-400 mt-1">
            Predictive modeling bridges NASA raw sensor data to proactive civil engineering decisions.
          </p>
        </div>

        {/* Right: Sector Deep-Dive & Action Plan */}
        <div className="lg:col-span-2 dark-clay-inset rounded-2xl p-3 sm:p-3.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-1.5 border-b border-white/10">
              <div>
                <h4 className="text-sm font-bold text-white">{currentSector.title}</h4>
                <p className="text-[10px] text-slate-400">Decision Window: {currentSector.decisionWindow}</p>
              </div>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Actionable Playbook
              </span>
            </div>

            <p className="text-xs text-slate-300 mt-2 mb-2 leading-relaxed">
              {currentSector.summary}
            </p>

            <div className="flex flex-col gap-1.5 my-2">
              <span className="text-[10.5px] font-bold text-sky-300">Operational Decision Protocol:</span>
              {currentSector.actions.map((act, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                  <span className="w-4 h-4 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30 text-[9px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span>{act}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-white/10 bg-white/5 p-2 rounded-xl border border-white/10">
            <span className="text-[10.5px] font-bold text-emerald-300 block">Quantified Societal & Economic Benefit:</span>
            <p className="text-xs text-slate-200 font-medium mt-0.5">{currentSector.benefit}</p>
          </div>
        </div>
      </div>

      {/* 3. BOTTOM: INTERACTIVE HORIZON SIMULATOR & LAUNCH FORECAST */}
      <div className="dark-clay-card-sm rounded-2xl p-3 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex flex-col gap-1 flex-1 min-w-[240px]">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="font-bold text-white">
              Multi-Year Projection Horizon ({activeHorizon} Years Ahead):
            </span>
            <span className="font-bold text-indigo-300 bg-indigo-500/20 px-2 py-0.5 rounded-full border border-indigo-500/30">
              Expected Shift: {signed(projectedHorizonShift, 2)} {variable.unit}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="range"
              min="1"
              max="10"
              value={activeHorizon}
              onChange={(e) => setActiveHorizon(Number(e.target.value))}
              className="flex-1 h-2 bg-slate-700 rounded-full appearance-none cursor-pointer accent-[#38bdf8]"
            />
            <span className="text-xs font-mono font-bold text-sky-400 w-12 text-right">
              +{activeHorizon} Yrs
            </span>
          </div>
        </div>

        <Link
          href={`/forecast?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(
            region.name
          )}&variable=${variable.key}&horizon=${activeHorizon}`}
          className="dark-clay-button rounded-xl px-4 py-2 bg-gradient-to-r from-sky-600 to-teal-600 text-white font-bold text-xs flex items-center gap-2 hover:brightness-110 active:scale-95 shadow-lg border border-sky-400/30"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          <span>Launch Full Scenario Forecast</span>
        </Link>
      </div>
    </div>
  );
}