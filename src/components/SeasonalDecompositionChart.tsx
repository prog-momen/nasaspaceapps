"use client";

import React, { useRef, useState } from "react";
import { dateToX } from "./charts/Charts";

export interface SeasonalDecompositionPoint {
  date: string;
  observed: number;
  trend: number;
  seasonal: number;
  residual: number;
  x: number;
}

interface Props {
  series: { date: string; value: number; trend: number; anomaly: number }[];
  seasonalClimatology: number[]; // 12 monthly values
  unit: string;
  variableName: string;
}

const W = 800;
const PAD = { l: 56, r: 16, t: 4, b: 14 };

function niceTicks(min: number, max: number, count = 3): number[] {
  if (min === max) return [min];
  const raw = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) {
    out.push(+v.toFixed(10));
  }
  return out;
}

const fmt = (v: number) =>
  Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2);

const signed = (v: number) => `${v >= 0 ? "+" : ""}${fmt(v)}`;

export default function SeasonalDecompositionChart({
  series,
  seasonalClimatology,
  unit,
  variableName,
}: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [activeLayer, setActiveLayer] = useState<"all" | "observed" | "trend" | "seasonal" | "residual">("all");
  const [overlayTrend, setOverlayTrend] = useState<boolean>(false);

  if (!series.length || seasonalClimatology.length !== 12) return null;

  const climMean = seasonalClimatology.reduce((s, x) => s + x, 0) / 12;

  const data: SeasonalDecompositionPoint[] = series.map((s) => {
    const month = Number(s.date.slice(5, 7));
    const seasonal = seasonalClimatology[month - 1] - climMean;
    const residual = s.value - s.trend - seasonal;
    return {
      date: s.date,
      observed: s.value,
      trend: s.trend,
      seasonal,
      residual,
      x: dateToX(s.date),
    };
  });

  const xs = data.map((d) => d.x);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);

  const sx = (x: number) => PAD.l + ((x - x0) / (x1 - x0 || 1)) * (W - PAD.l - PAD.r);

  // Find extreme residual spikes for interactive jump
  const residuals = data.map((d) => d.residual);
  const maxResidualIdx = residuals.indexOf(Math.max(...residuals));
  const minResidualIdx = residuals.indexOf(Math.min(...residuals));

  const allPanes = [
    {
      id: "observed" as const,
      name: "Observed (Y_t)",
      subtitle: `Raw ${variableName.toLowerCase()} measurements`,
      color: "#38bdf8",
      values: data.map((d) => d.observed),
      drawZero: false,
    },
    {
      id: "trend" as const,
      name: "Trend (T_t)",
      subtitle: "Deseasonalized linear drift",
      color: "#f59e0b",
      values: data.map((d) => d.trend),
      drawZero: false,
    },
    {
      id: "seasonal" as const,
      name: "Seasonal (S_t)",
      subtitle: "12-month annual cycle (mean = 0)",
      color: "#34d399",
      values: data.map((d) => d.seasonal),
      drawZero: true,
    },
    {
      id: "residual" as const,
      name: "Residual (R_t)",
      subtitle: "Stochastic noise & anomaly shocks",
      color: "#c084fc",
      values: data.map((d) => d.residual),
      drawZero: true,
    },
  ];

  const visiblePanes = activeLayer === "all" ? allPanes : allPanes.filter((p) => p.id === activeLayer);

  const PANE_H = activeLayer === "all" ? 64 : 180;
  const totalSvgHeight = PANE_H * visiblePanes.length;

  const yearStep = Math.max(2, Math.round((x1 - x0) / 6));
  const xTicks: number[] = [];
  for (let yr = Math.ceil(x0); yr <= Math.floor(x1); yr += yearStep) {
    xTicks.push(yr);
  }

  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const currX = x0 + ((px - PAD.l) / (W - PAD.l - PAD.r)) * (x1 - x0);

    let bestIdx = 0;
    let bestDist = Math.abs(data[0].x - currX);
    for (let i = 1; i < data.length; i++) {
      const dist = Math.abs(data[i].x - currX);
      if (dist < bestDist) {
        bestDist = dist;
        bestIdx = i;
      }
    }
    setHoverIndex(bestIdx);
  };

  const hoveredPoint = hoverIndex !== null ? data[hoverIndex] : null;

  return (
    <div className="h-full flex flex-col justify-between select-none">
      {/* Top Interactive Telemetry Ribbon (No cards, borderless HUD) */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2 shrink-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#2563eb]/20 text-[#60a5fa] border border-[#2563eb]/40 font-bold uppercase">
            Additive Model: Y_t = T_t + S_t + R_t
          </span>

          {/* Interactive Layer Filter Buttons */}
          <div className="flex items-center gap-1 text-[11px] font-medium">
            <button
              onClick={() => setActiveLayer("all")}
              className={`px-2 py-0.5 rounded-lg border transition-all ${
                activeLayer === "all"
                  ? "bg-[#2563eb] border-blue-400 text-white font-bold"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
              }`}
            >
              All 4 Panes
            </button>
            <button
              onClick={() => setActiveLayer("trend")}
              className={`px-2 py-0.5 rounded-lg border transition-all ${
                activeLayer === "trend"
                  ? "bg-[#f59e0b] border-amber-400 text-black font-bold"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
              }`}
            >
              Solo Trend
            </button>
            <button
              onClick={() => setActiveLayer("seasonal")}
              className={`px-2 py-0.5 rounded-lg border transition-all ${
                activeLayer === "seasonal"
                  ? "bg-[#34d399] border-emerald-400 text-black font-bold"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
              }`}
            >
              Solo Seasonal
            </button>
            <button
              onClick={() => setActiveLayer("residual")}
              className={`px-2 py-0.5 rounded-lg border transition-all ${
                activeLayer === "residual"
                  ? "bg-[#c084fc] border-purple-400 text-black font-bold"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
              }`}
            >
              Solo Residual
            </button>
            <button
              onClick={() => setOverlayTrend((prev) => !prev)}
              className={`px-2 py-0.5 rounded-lg border transition-all ${
                overlayTrend
                  ? "bg-amber-500/20 border-amber-400 text-amber-300 font-bold"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-white"
              }`}
              title="Overlay linear trend directly on observed series"
            >
              {overlayTrend ? "Trend Overlay: ON" : "Overlay Trend"}
            </button>
          </div>
        </div>

        {/* Interactive Extreme Anomaly Jumpers */}
        <div className="flex items-center gap-1.5 text-[10px] font-mono">
          <span className="text-[#6b7280]">Anomalies:</span>
          <button
            onClick={() => setHoverIndex(maxResidualIdx)}
            className="px-2 py-0.5 rounded bg-rose-500/20 border border-rose-500/30 text-rose-300 hover:bg-rose-500/30 transition-colors"
          >
            Max Heat Spike ({data[maxResidualIdx].date})
          </button>
          <button
            onClick={() => setHoverIndex(minResidualIdx)}
            className="px-2 py-0.5 rounded bg-sky-500/20 border border-sky-500/30 text-sky-300 hover:bg-sky-500/30 transition-colors"
          >
            Min Dip ({data[minResidualIdx].date})
          </button>
        </div>
      </div>

      {/* Live Synchronized Readout Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 py-1 px-2 my-1 text-xs font-mono bg-white/5 rounded-lg shrink-0">
        {hoveredPoint ? (
          <>
            <span className="text-white font-bold">{hoveredPoint.date}</span>
            <span className="text-[#38bdf8]">Obs: {fmt(hoveredPoint.observed)} {unit}</span>
            <span className="text-[#f59e0b]">Trend: {fmt(hoveredPoint.trend)}</span>
            <span className="text-[#34d399]">Seasonal: {signed(hoveredPoint.seasonal)}</span>
            <span className="text-[#c084fc]">Residual: {signed(hoveredPoint.residual)}</span>
            <span className="text-[#9ca3af] hidden sm:inline">
              [Sum check: {(hoveredPoint.trend + hoveredPoint.seasonal + hoveredPoint.residual).toFixed(2)} === {fmt(hoveredPoint.observed)}]
            </span>
          </>
        ) : (
          <span className="text-[#9ca3af] text-[11px] italic">
            Move mouse along any track to scrub all 4 components simultaneously
          </span>
        )}
      </div>

      {/* Synchronized Multi-Track SVG Chart (Full Width, Zero Card Borders) */}
      <div className="flex-1 min-h-0 flex items-center justify-center">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${totalSvgHeight}`}
          className="w-full h-full max-h-[300px] touch-pan-y select-none"
          onPointerMove={onPointerMove}
          onPointerLeave={() => setHoverIndex(null)}
          role="img"
        >
          {visiblePanes.map((pane, paneIdx) => {
            const yMinRaw = Math.min(...pane.values);
            const yMaxRaw = Math.max(...pane.values);
            const padY = (yMaxRaw - yMinRaw || 1) * 0.12;
            const y0 = pane.drawZero ? Math.min(0, yMinRaw) - padY : yMinRaw - padY;
            const y1 = pane.drawZero ? Math.max(0, yMaxRaw) + padY : yMaxRaw + padY;

            const topY = paneIdx * PANE_H;
            const sy = (y: number) =>
              topY + PANE_H - PAD.b - ((y - y0) / (y1 - y0 || 1)) * (PANE_H - PAD.t - PAD.b);

            const yTicks = niceTicks(y0, y1, 2);
            const pathD = data
              .map((d, i) => `${i ? "L" : "M"}${sx(d.x).toFixed(1)},${sy(pane.values[i]).toFixed(1)}`)
              .join("");

            const trendOverlayPathD = overlayTrend && pane.id === "observed"
              ? data.map((d, i) => `${i ? "L" : "M"}${sx(d.x).toFixed(1)},${sy(d.trend).toFixed(1)}`).join("")
              : null;

            return (
              <g key={pane.id}>
                {/* Horizontal Lane Divider */}
                {paneIdx > 0 && (
                  <line
                    x1={PAD.l}
                    x2={W - PAD.r}
                    y1={topY}
                    y2={topY}
                    stroke="#1f2937"
                    strokeDasharray="2 3"
                  />
                )}

                {/* Track Title */}
                <text x={PAD.l} y={topY + 11} fontSize="10" fontWeight="700" fill={pane.color}>
                  {pane.name}
                </text>
                <text x={W - PAD.r} y={topY + 11} fontSize="8.5" textAnchor="end" fill="#6b7280">
                  {pane.subtitle}
                </text>

                {/* Zero Line for Seasonal & Residual */}
                {pane.drawZero && y0 <= 0 && y1 >= 0 && (
                  <line
                    x1={PAD.l}
                    x2={W - PAD.r}
                    y1={sy(0)}
                    y2={sy(0)}
                    stroke="#4b5563"
                    strokeDasharray="3 3"
                    strokeWidth="0.8"
                  />
                )}

                {/* Y Ticks & Grid */}
                {yTicks.map((tick) => (
                  <g key={tick}>
                    <line
                      x1={PAD.l}
                      x2={W - PAD.r}
                      y1={sy(tick)}
                      y2={sy(tick)}
                      stroke="#111827"
                      strokeWidth="0.8"
                    />
                    <text
                      x={PAD.l - 6}
                      y={sy(tick) + 3}
                      textAnchor="end"
                      fontSize="8.5"
                      fill="#9ca3af"
                      fontFamily="monospace"
                    >
                      {fmt(tick)}
                    </text>
                  </g>
                ))}

                {/* Main Curve */}
                <path
                  d={pathD}
                  fill="none"
                  stroke={pane.color}
                  strokeWidth={pane.id === "trend" ? "2.2" : "1.4"}
                  strokeLinejoin="round"
                />

                {/* Optional Trend Overlay onto Observed Lane */}
                {trendOverlayPathD && (
                  <path
                    d={trendOverlayPathD}
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="2"
                    strokeDasharray="4 3"
                  />
                )}

                {/* X-Axis Labels on Bottom Track */}
                {paneIdx === visiblePanes.length - 1 &&
                  xTicks.map((yr) => (
                    <text
                      key={yr}
                      x={sx(yr)}
                      y={topY + PANE_H - 2}
                      textAnchor="middle"
                      fontSize="9"
                      fill="#9ca3af"
                      fontFamily="monospace"
                    >
                      {yr}
                    </text>
                  ))}

                {/* Active Hover Point */}
                {hoveredPoint && (
                  <circle
                    cx={sx(hoveredPoint.x)}
                    cy={sy(pane.values[hoverIndex!])}
                    r="3.5"
                    fill={pane.color}
                    stroke="#ffffff"
                    strokeWidth="1.5"
                  />
                )}
              </g>
            );
          })}

          {/* Synchronized Vertical Crosshair line */}
          {hoveredPoint && (
            <line
              x1={sx(hoveredPoint.x)}
              x2={sx(hoveredPoint.x)}
              y1={0}
              y2={totalSvgHeight}
              stroke="#94a3b8"
              strokeWidth="1.2"
              strokeDasharray="3 3"
            />
          )}
        </svg>
      </div>

      {/* Component Footers: Telemetry Columns (Zero Cards) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-white/10 text-[11px] shrink-0">
        <div>
          <span className="font-bold text-[#38bdf8] block">1. Observed (Y_t)</span>
          <p className="text-[#9ca3af] text-[10px] leading-snug mt-0.5">
            Raw observational satellite series combining cyclic solar seasons, systematic planetary drift, and local weather.
          </p>
        </div>
        <div>
          <span className="font-bold text-[#f59e0b] block">2. Linear Trend (T_t)</span>
          <p className="text-[#9ca3af] text-[10px] leading-snug mt-0.5">
            Underlying persistent direction of environmental drift after subtracting the 12-month seasonal climatology.
          </p>
        </div>
        <div>
          <span className="font-bold text-[#34d399] block">3. Seasonal (S_t)</span>
          <p className="text-[#9ca3af] text-[10px] leading-snug mt-0.5">
            Repeating 12-month harmonic signature driven by solar angle. Fluctuations sum strictly to zero each year.
          </p>
        </div>
        <div>
          <span className="font-bold text-[#c084fc] block">4. Residual (R_t)</span>
          <p className="text-[#9ca3af] text-[10px] leading-snug mt-0.5">
            Unmodeled stochastic shocks and extreme anomalies (flash droughts, intense heatwaves, and storms).
          </p>
        </div>
      </div>
    </div>
  );
}
