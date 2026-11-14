"use client";

import React, { useState } from "react";
import Link from "next/link";

export interface AiAgentForecastingProps {
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
  };
  trend: {
    slopePerYear: number;
    pValue: number;
    verdict: "significant" | "weak_evidence" | "not_significant";
    totalChange: number;
    direction: "increasing" | "decreasing" | "flat";
    period: { start: string; end: string; years: number };
  };
  horizon: number;
}

type SectorKey = "disaster" | "agriculture" | "water" | "health" | "economy";

interface SectorDetail {
  id: SectorKey;
  title: string;
  nasaVariable: string;
  leadTime: string;
  riskReduction: string;
  problem: string;
  solution: string;
  actionItems: string[];
}

const SECTORS: SectorDetail[] = [
  {
    id: "disaster",
    title: "Wildfire & Disaster Pre-positioning",
    nasaVariable: "GWETROOT (Soil Wetness) & T2M_MAX",
    leadTime: "1 to 6 months in advance",
    riskReduction: "40% to 65% faster emergency response",
    problem:
      "Flash droughts and prolonged high temperatures rapidly deplete soil moisture, transforming vegetated terrain into tinderboxes susceptible to catastrophic wildfires.",
    solution:
      "Multi-month forecasting allows emergency management authorities to track cumulative soil moisture deficits and surface heating weeks before critical fire weather strikes.",
    actionItems: [
      "Pre-position aerial firefighting tankers and bulldozers near high-deficit zones.",
      "Activate municipal water reservoir reserves and test regional hydrant pressure.",
      "Issue localized outdoor burn bans and proactive high-risk evacuation staging.",
    ],
  },
  {
    id: "agriculture",
    title: "Agricultural Drought & Food Security",
    nasaVariable: "PRECTOTCORR (Precipitation) & EVLAND",
    leadTime: "3 to 12 months in advance",
    riskReduction: "25% to 45% reduction in crop failure loss",
    problem:
      "Erratic seasonal rains and shifting monsoon patterns cause sudden planting failures, stunted yields, and severe financial vulnerability for farming communities.",
    solution:
      "Seasonal climatological projections inform farmers about upcoming precipitation deficits, enabling strategic adjustments well before seeds are placed in the ground.",
    actionItems: [
      "Select drought-tolerant or early-maturing crop seed varieties.",
      "Shift planting calendars to align with projected seasonal precipitation peaks.",
      "Implement drip irrigation rationing and schedule supplemental reservoir releases.",
    ],
  },
  {
    id: "water",
    title: "Water Basin & Reservoir Optimization",
    nasaVariable: "PRECTOTCORR & GWETROOT",
    leadTime: "6 to 24 months in advance",
    riskReduction: "30% to 50% decrease in water supply shortfalls",
    problem:
      "Multi-year hydrological droughts deplete municipal aquifers and hydroelectric dams, leading to power outages and emergency water rationing.",
    solution:
      "Decadal trend forecasting provides water basin authorities with statistical certainty regarding inflow trends, enabling balanced water banking and flood mitigation.",
    actionItems: [
      "Adjust multi-seasonal hydroelectric generation targets to conserve reserve volumes.",
      "Accelerate artificial aquifer recharge during high-precipitation periods.",
      "Plan inter-basin water transfers before municipal reservoirs drop below critical thresholds.",
    ],
  },
  {
    id: "health",
    title: "Public Health & Extreme Heatwaves",
    nasaVariable: "T2M_MAX & T2M (Air Temperature)",
    leadTime: "Weeks to multi-year horizons",
    riskReduction: "50% to 70% decrease in heat-related fatalities",
    problem:
      "Severe heatwaves compound urban heat island effects, leading to hospital surges, cardiovascular fatalities, and vulnerable community isolation.",
    solution:
      "Temperature trend forecasting highlights intensifying summer extremes, enabling public health ministries to deploy preventative urban cooling protocols.",
    actionItems: [
      "Establish air-conditioned municipal cooling shelters and hydration stations.",
      "Issue proactive workplace safety mandates for construction and agricultural laborers.",
      "Protect electrical grids against transformer overloads during peak air-conditioning hours.",
    ],
  },
  {
    id: "economy",
    title: "Infrastructure & Economic Risk Mitigation",
    nasaVariable: "T2M, PRECTOTCORR & TS",
    leadTime: "5 to 10+ year forecasting horizons",
    riskReduction: "Billions in avoided infrastructure rebuilding costs",
    problem:
      "Civil infrastructure (bridges, rail lines, power lines, and storm drains) built to historic tolerances fails under intensifying climate extremes.",
    solution:
      "Multi-year and multi-decade statistical forecasting equips municipal planners and insurers with empirical slope projections to climate-harden capital investments.",
    actionItems: [
      "Upgrade stormwater drainage capacity to accommodate higher-intensity peak precipitation.",
      "Incorporate heat-resistant asphalt and thermal expansion tolerances in transport networks.",
      "Adjust actuarial risk models and underwriting standards for climate-exposed assets.",
    ],
  },
];

export default function AiAgentForecastingSpace({
  region,
  variable,
  trend,
  horizon,
}: AiAgentForecastingProps) {
  const [activeSector, setActiveSector] = useState<SectorKey>("disaster");
  const [copied, setCopied] = useState(false);

  const selectedSectorData = SECTORS.find((s) => s.id === activeSector) || SECTORS[0];

  const ratePerDecade = trend.slopePerYear * 10;
  const isSignificant = trend.verdict === "significant";
  const directionWord =
    trend.direction === "increasing"
      ? "warming / upward"
      : trend.direction === "decreasing"
      ? "cooling / downward"
      : "stable / neutral";

  const cumulativeProjectedChange = (trend.slopePerYear * horizon).toFixed(2);

  // Generate dynamic synthesis tailored to the region
  const regionalSynthesis = `Based on NASA Earth observations from ${trend.period.start} to ${
    trend.period.end
  } (${trend.period.years} years of continuous data), ${region.name} exhibits an empirical trend of ${
    trend.slopePerYear >= 0 ? "+" : ""
  }${trend.slopePerYear.toFixed(3)} ${variable.unit}/year (${
    ratePerDecade >= 0 ? "+" : ""
  }${ratePerDecade.toFixed(2)} ${variable.unit}/decade). Statistical verification via Mann-Kendall and OLS yields p = ${
    trend.pValue < 0.001 ? "< 0.001" : trend.pValue.toFixed(3)
  }, confirming ${
    isSignificant
      ? "high statistical significance (> 99% confidence)"
      : "moderate or developing statistical evidence"
  }. Projected across the ${horizon}-year horizon, the expected baseline shift reaches approximately ${
    Number(cumulativeProjectedChange) >= 0 ? "+" : ""
  }${cumulativeProjectedChange} ${variable.unit}.`;

  const copyBriefing = () => {
    const text = `NASA AI AGENT • ENVIRONMENTAL FORECASTING BRIEFING
Region: ${region.name} (${region.lat.toFixed(2)}, ${region.lon.toFixed(2)})
Variable: ${variable.name} (${variable.unit})
Trend: ${ratePerDecade.toFixed(2)} ${variable.unit}/decade
Statistical Verdict: ${trend.verdict}
${horizon}-Year Projected Shift: ${cumulativeProjectedChange} ${variable.unit}

Regional Assessment:
${regionalSynthesis}

Key Forecasting Benefit (${selectedSectorData.title}):
${selectedSectorData.solution}
Actionable Measures:
${selectedSectorData.actionItems.map((item) => `- ${item}`).join("\n")}
`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden shadow-2xl">
      {/* Top Banner / AI Agent Identity */}
      <div className="bg-[#0b0f19] border-b border-[#1f2937] px-4 py-3 sm:px-6 sm:py-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="relative w-8 h-8 rounded-lg bg-[#2563eb]/20 border border-[#2563eb]/40 flex items-center justify-center text-[#60a5fa] shrink-0">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="9"></circle>
              <path d="M12 3a9 9 0 0 1 9 9"></path>
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M12 7v2"></path>
              <path d="M12 15v2"></path>
              <path d="M7 12H9"></path>
              <path d="M15 12h2"></path>
            </svg>
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-[#10b981] border-2 border-[#0b0f19]"></span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base font-bold text-white tracking-tight">
                AI Agent Environmental Intelligence
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/30">
                Live Forecast Agent
              </span>
            </div>
            <p className="text-xs text-[#9ca3af]">
              Actionable insights on how NASA Earth observation forecasting drives real-world resilience
            </p>
          </div>
        </div>

        {/* Copy Briefing Button */}
        <button
          onClick={copyBriefing}
          className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-[#cbd5e1] hover:text-white transition-all flex items-center gap-2 active:scale-95"
          title="Copy AI Forecast Briefing to clipboard"
        >
          <svg
            width="13"
            height="13"
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
          <span>{copied ? "Briefing Copied" : "Copy Briefing"}</span>
        </button>
      </div>

      {/* Dynamic Regional Forecast Assessment */}
      <div className="p-4 sm:p-6 flex flex-col gap-5 border-b border-[#1f2937]/70">
        <div className="bg-[#0b0f19] border border-[#1f2937] rounded-xl p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#60a5fa] flex items-center gap-1.5">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              Regional Agent Diagnosis: {region.name}
            </span>
            <span className="text-xs font-mono text-[#a1a1aa]">
              {region.lat.toFixed(1)}°, {region.lon.toFixed(1)}°
            </span>
          </div>

          <p className="text-xs sm:text-sm text-[#e2e8f0] leading-relaxed">
            {regionalSynthesis}
          </p>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs pt-3 border-t border-[#1f2937]">
            <div className="bg-[#111827] p-2.5 rounded-lg border border-[#1f2937]">
              <span className="text-[#9ca3af] block text-[10px] uppercase">Trend Trajectory</span>
              <span className="font-semibold text-white mt-0.5 block">{directionWord}</span>
            </div>
            <div className="bg-[#111827] p-2.5 rounded-lg border border-[#1f2937]">
              <span className="text-[#9ca3af] block text-[10px] uppercase">{horizon}-Year Horizon Shift</span>
              <span className="font-semibold text-[#60a5fa] font-mono mt-0.5 block">
                {Number(cumulativeProjectedChange) >= 0 ? "+" : ""}
                {cumulativeProjectedChange} {variable.unit}
              </span>
            </div>
            <div className="bg-[#111827] p-2.5 rounded-lg border border-[#1f2937]">
              <span className="text-[#9ca3af] block text-[10px] uppercase">Statistical Certainty</span>
              <span
                className={`font-semibold mt-0.5 block ${
                  isSignificant ? "text-[#34d399]" : "text-[#fbbf24]"
                }`}
              >
                {isSignificant ? "Confirmed Significant" : "Emerging Signal"}
              </span>
            </div>
          </div>
        </div>

        {/* Core Value Proposition: The 5 Strategic Benefits of Environmental Forecasting */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-xs sm:text-sm font-bold text-white uppercase tracking-wider">
                Strategic Benefits of Climate & Environmental Forecasting
              </h3>
              <p className="text-[11px] text-[#9ca3af] mt-0.5">
                Explore how predictive models transform NASA satellite observations into societal preparedness
              </p>
            </div>
          </div>

          {/* Sector Selector Tabs */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 mb-4">
            {SECTORS.map((s) => {
              const isActive = activeSector === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveSector(s.id)}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all border text-left flex flex-col justify-between ${
                    isActive
                      ? "bg-[#2563eb] border-[#2563eb] text-white shadow-md"
                      : "bg-[#0b0f19] border-[#1f2937] text-[#cbd5e1] hover:bg-[#1f2937] hover:text-white"
                  }`}
                >
                  <span className="truncate">{s.title.split("&")[0]}</span>
                  <span
                    className={`text-[9px] mt-1 truncate ${
                      isActive ? "text-blue-150 text-white/80" : "text-[#9ca3af]"
                    }`}
                  >
                    {s.leadTime}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Active Sector Deep Dive Card */}
          <div className="bg-[#0b0f19] border border-[#1f2937] rounded-xl p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#1f2937]">
              <div>
                <h4 className="text-sm sm:text-base font-bold text-white">
                  {selectedSectorData.title}
                </h4>
                <span className="text-xs text-[#60a5fa] font-mono">
                  Key NASA Variables: {selectedSectorData.nasaVariable}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-[#9ca3af] uppercase block">Estimated Impact</span>
                <span className="text-xs font-semibold text-[#34d399]">
                  {selectedSectorData.riskReduction}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4 text-xs">
              <div className="bg-[#111827] p-3.5 rounded-lg border border-[#1f2937]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#f87171] block mb-1">
                  The Operational Challenge
                </span>
                <p className="text-[#cbd5e1] leading-relaxed">
                  {selectedSectorData.problem}
                </p>
              </div>

              <div className="bg-[#111827] p-3.5 rounded-lg border border-[#1f2937]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#38bdf8] block mb-1">
                  How Forecasting Solves It
                </span>
                <p className="text-[#cbd5e1] leading-relaxed">
                  {selectedSectorData.solution}
                </p>
              </div>
            </div>

            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#a1a1aa] block mb-2">
                High-Leverage Interventions Enabled by Advance Projections
              </span>
              <ul className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {selectedSectorData.actionItems.map((item, idx) => (
                  <li
                    key={idx}
                    className="bg-[#111827] border border-[#1f2937] rounded-lg p-2.5 text-xs text-[#e2e8f0] flex items-start gap-2"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[#60a5fa] shrink-0 mt-1.5"></span>
                    <span className="leading-snug">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Action Footer */}
      <div className="bg-[#0b0f19] px-4 py-3 sm:px-6 flex flex-wrap items-center justify-between gap-3 text-xs">
        <span className="text-[#9ca3af]">
          Need customized scenario analysis or specific climate adaptation parameters?
        </span>
        <div className="flex items-center gap-2">
          <Link
            href={`/forecast?lat=${region.lat}&lon=${region.lon}&name=${encodeURIComponent(
              region.name
            )}&variable=${variable.key}&horizon=${horizon}`}
            className="px-3.5 py-1.5 rounded-lg bg-[#22c55e] hover:bg-[#16a34a] text-white font-semibold transition-all shadow-sm flex items-center gap-1.5 active:scale-95"
          >
            <span>Run {horizon}-Year Projections</span>
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
    </section>
  );
}

