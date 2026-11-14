"use client";

import React, { useRef, useState, useMemo } from "react";
import { dateToX, LineChart, LineSeries } from "../charts/Charts";

interface Props {
  series: { date: string; value: number; trend: number; anomaly: number }[];
  seasonalClimatology: number[];
  unit: string;
  variableName: string;
  yearsSpan: number;
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

export default function TimeSeriesDecompositionPart({
  series,
  seasonalClimatology,
  unit,
  variableName,
  yearsSpan,
}: Props) {
  const [viewMode, setViewMode] = useState<"both" | "timeseries" | "decomposition">("both");
  const [timeWindow, setTimeWindow] = useState<"all" | "20y" | "10y">("all");
  const [showMovingAvg, setShowMovingAvg] = useState(true);
  const [showChartGuide, setShowChartGuide] = useState(false);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const svgRef = useRef<SVGSVGElement | null>(null);

  const climMean = seasonalClimatology.reduce((s, x) => s + x, 0) / 12;

  // Filter series based on window
  const filteredSeries = useMemo(() => {
    if (timeWindow === "all") return series;
    const endYear = Number(series[series.length - 1].date.slice(0, 4));
    const startYear = timeWindow === "10y" ? endYear - 10 : endYear - 20;
    return series.filter((s) => Number(s.date.slice(0, 4)) >= startYear);
  }, [series, timeWindow]);

  // Moving average
  const movingAvgSeries = useMemo(() => {
    const pts = filteredSeries.map((s) => ({ x: dateToX(s.date), y: s.value }));
    const result: { x: number; y: number }[] = [];
    for (let i = 0; i < pts.length; i++) {
      const start = Math.max(0, i - 11);
      const slice = pts.slice(start, i + 1);
      const avg = slice.reduce((acc, p) => acc + p.y, 0) / slice.length;
      result.push({ x: pts[i].x, y: avg });
    }
    return result;
  }, [filteredSeries]);

  const chartSeries: LineSeries[] = useMemo(() => {
    const list: LineSeries[] = [
      {
        name: "Observed",
        color: "#38bdf8",
        points: filteredSeries.map((s) => ({ x: dateToX(s.date), y: s.value })),
        width: 1.8,
      },
    ];
    if (showMovingAvg) {
      list.push({
        name: "12M Moving Avg",
        color: "#f59e0b",
        points: movingAvgSeries,
        width: 2.4,
      });
    }
    return list;
  }, [filteredSeries, movingAvgSeries, showMovingAvg]);

  // Decomposition points
  const decompData = useMemo(() => {
    return filteredSeries.map((s) => {
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
  }, [filteredSeries, seasonalClimatology, climMean]);

  const xs = decompData.map((d) => d.x);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const sx = (x: number) => PAD.l + ((x - x0) / (x1 - x0 || 1)) * (W - PAD.l - PAD.r);

  // Jumpers
  const residuals = decompData.map((d) => d.residual);
  const maxResIdx = residuals.indexOf(Math.max(...residuals));
  const minResIdx = residuals.indexOf(Math.min(...residuals));

  const panes = [
    {
      id: "observed",
      name: "1. Observed Phenomenon (Y_t)",
      subtitle: "Raw monthly satellite observations (NASA POWER)",
      color: "#38bdf8",
      values: decompData.map((d) => d.observed),
      drawZero: false,
    },
    {
      id: "trend",
      name: "2. Trend Component (T_t)",
      subtitle: "Deseasonalized decadal secular drift",
      color: "#f59e0b",
      values: decompData.map((d) => d.trend),
      drawZero: false,
    },
    {
      id: "seasonal",
      name: "3. Seasonal Component (S_t)",
      subtitle: "12-month solar/astronomical cyclic oscillation",
      color: "#34d399",
      values: decompData.map((d) => d.seasonal),
      drawZero: true,
    },
    {
      id: "residual",
      name: "4. Residual Component (R_t)",
      subtitle: "Stochastic noise & acute weather anomaly shocks",
      color: "#c084fc",
      values: decompData.map((d) => d.residual),
      drawZero: true,
    },
  ];

  const PANE_H = viewMode === "both" ? 40 : 60;
  const totalSvgH = PANE_H * panes.length;

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
    let bestDist = Math.abs(decompData[0].x - currX);
    for (let i = 1; i < decompData.length; i++) {
      const dist = Math.abs(decompData[i].x - currX);
      if (dist < bestDist) {
        bestDist = dist;
        bestIdx = i;
      }
    }
    setHoverIndex(bestIdx);
  };

  const hovered = hoverIndex !== null ? decompData[hoverIndex] : null;

  return (
    <div className="dark-clay-card rounded-2xl sm:rounded-3xl p-3 sm:p-4 h-full flex flex-col justify-between gap-2.5 select-none text-slate-100 font-sans">
      {/* 1. TOP HEADER & CONTROLS */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30 uppercase">
            Part 2: Time Series & Seasonal Decomposition
          </span>
          <span className="text-xs text-slate-400 hidden sm:inline">
            {variableName} ({unit}) • {yearsSpan} Years Record
          </span>
        </div>

        {/* View mode & zoom buttons */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
          {/* Mode Switcher */}
          <div className="flex items-center gap-1 dark-clay-inset p-1 rounded-xl">
            <button
              onClick={() => setViewMode("both")}
              className={`px-2 py-0.5 rounded-lg text-[11px] transition-all ${
                viewMode === "both"
                  ? "bg-sky-500 text-white font-bold shadow-md shadow-sky-900/50"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Dual View
            </button>
            <button
              onClick={() => setViewMode("timeseries")}
              className={`px-2 py-0.5 rounded-lg text-[11px] transition-all ${
                viewMode === "timeseries"
                  ? "bg-sky-500 text-white font-bold shadow-md shadow-sky-900/50"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Time Series
            </button>
            <button
              onClick={() => setViewMode("decomposition")}
              className={`px-2 py-0.5 rounded-lg text-[11px] transition-all ${
                viewMode === "decomposition"
                  ? "bg-sky-500 text-white font-bold shadow-md shadow-sky-900/50"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              4-Component
            </button>
          </div>

          {/* Window Filter */}
          <div className="flex items-center gap-1 dark-clay-inset p-1 rounded-xl">
            {(["all", "20y", "10y"] as const).map((w) => (
              <button
                key={w}
                onClick={() => setTimeWindow(w)}
                className={`px-2 py-0.5 rounded-lg text-[10.5px] uppercase font-mono transition-all ${
                  timeWindow === w
                    ? "bg-white text-slate-900 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {w}
              </button>
            ))}
          </div>

          {/* Moving Average Toggle */}
          <button
            onClick={() => setShowMovingAvg((p) => !p)}
            className={`px-2.5 py-1 rounded-xl text-[10.5px] font-semibold border transition-all ${
              showMovingAvg
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold shadow-sm"
                : "dark-clay-button text-slate-400 hover:text-white"
            }`}
          >
            12M Moving Avg
          </button>

          {/* About Charts Toggle Button */}
          <button
            onClick={() => setShowChartGuide((p) => !p)}
            className="text-[10.5px] font-bold text-sky-400 hover:text-sky-300 px-2.5 py-1 rounded-xl dark-clay-button flex items-center gap-1"
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span>{showChartGuide ? "Hide Info" : "Chart Guide"}</span>
          </button>
        </div>
      </div>

      {/* 2. DEDICATED INFO STRIP EXPLAINING THE CHARTS (If Guide Active) */}
      {showChartGuide && (
        <div className="dark-clay-inset rounded-2xl p-3 text-xs shrink-0 border border-sky-500/30 space-y-2">
          <div className="flex items-center justify-between pb-1.5 border-b border-white/10">
            <strong className="text-sky-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-sky-400"></span>
              Comprehensive Scientific Guide: Time Series & Additive Decomposition
            </strong>
            <span className="text-[10px] font-mono text-slate-400">Additive Formula: Y_t = T_t + S_t + R_t</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-[11px]">
            <div className="p-2 rounded-xl bg-white/5 border border-sky-500/20">
              <span className="text-sky-400 font-bold block">1. Observed Series (Y_t)</span>
              <p className="text-slate-300 mt-0.5">
                Represents continuous NASA satellite sensor readings. Encapsulates all physical forces acting simultaneously: climate shifts, annual orbital seasons, and daily weather anomalies.
              </p>
            </div>
            <div className="p-2 rounded-xl bg-white/5 border border-amber-500/20">
              <span className="text-amber-400 font-bold block">2. Trend Component (T_t)</span>
              <p className="text-slate-300 mt-0.5">
                Deseasonalized secular drift. By removing the 12-month solar cycle, this component reveals whether the local climate is genuinely warming, cooling, or drying over multi-decadal scales.
              </p>
            </div>
            <div className="p-2 rounded-xl bg-white/5 border border-emerald-500/20">
              <span className="text-emerald-400 font-bold block">3. Seasonal (S_t)</span>
              <p className="text-slate-300 mt-0.5">
                Periodic 12-month astronomical oscillation. Shows the predictable summer maximums and winter minimums resulting from Earth&apos;s axial tilt and solar irradiance.
              </p>
            </div>
            <div className="p-2 rounded-xl bg-white/5 border border-purple-500/20">
              <span className="text-purple-400 font-bold block">4. Residual (R_t)</span>
              <p className="text-slate-300 mt-0.5">
                Stochastic noise and acute events. What remains after subtracting trend and season (R_t = Y_t - T_t - S_t). Large residual spikes represent extreme heatwaves or flash droughts.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 3. MAIN DISPLAY (TIME SERIES CHART & 4-COMPONENT SLOTS) */}
      <div className="flex-1 min-h-0 flex flex-col justify-between gap-2 overflow-hidden">
        {/* UPPER VIEW: TIME SERIES (IF 'both' OR 'timeseries') */}
        {(viewMode === "both" || viewMode === "timeseries") && (
          <div className={`${viewMode === "both" ? "h-36 sm:h-44" : "h-full"} dark-clay-inset rounded-2xl p-2.5 flex flex-col justify-between`}>
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-300 px-1">
              <div className="flex items-center gap-3">
                <span className="font-bold text-white flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#38bdf8]"></span>
                  Time Series Phenomenon Evolution (Y_t)
                </span>
                {showMovingAvg && (
                  <span className="text-amber-400 text-[10px] flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                    12M Rolling Average (Inter-annual Climate Drift)
                  </span>
                )}
              </div>
              <span className="text-slate-400">
                {filteredSeries.length} Months • {filteredSeries[0].date} to {filteredSeries[filteredSeries.length - 1].date}
              </span>
            </div>

            <div className="flex-1 min-h-0 w-full relative">
              <LineChart
                series={chartSeries}
                unit={unit}
                height={viewMode === "both" ? 120 : 260}
              />
            </div>
          </div>
        )}

        {/* LOWER VIEW: 4-COMPONENT SEASONAL DECOMPOSITION (IF 'both' OR 'decomposition') */}
        {(viewMode === "both" || viewMode === "decomposition") && (
          <div className="dark-clay-inset rounded-2xl p-2.5 flex flex-col justify-between flex-1 min-h-0">
            {/* Header with Hover readout and Anomaly jumpers */}
            <div className="flex flex-wrap items-center justify-between gap-1 text-[11px] font-mono pb-1 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="text-slate-300 font-bold">Synchronized Crosshair Scrubbing:</span>
                {hovered ? (
                  <span className="bg-white/10 px-2 py-0.5 rounded-md font-bold text-white border border-white/20 shadow-sm">
                    {hovered.date}: Y=<strong className="text-sky-400">{fmt(hovered.observed)}</strong> • T=<strong className="text-amber-400">{fmt(hovered.trend)}</strong> • S=<strong className="text-emerald-400">{signed(hovered.seasonal)}</strong> • R=<strong className="text-purple-400">{signed(hovered.residual)}</strong>
                  </span>
                ) : (
                  <span className="text-slate-500 italic">Hover crosshair over tracks to inspect values</span>
                )}
              </div>

              {/* Anomaly Jumpers */}
              <div className="flex items-center gap-1 text-[10px]">
                <span className="text-slate-400">Jump to Shock:</span>
                <button
                  onClick={() => setHoverIndex(maxResIdx)}
                  className="dark-clay-button px-2 py-0.5 rounded-lg text-emerald-400 font-bold"
                >
                  Max (+{fmt(decompData[maxResIdx].residual)})
                </button>
                <button
                  onClick={() => setHoverIndex(minResIdx)}
                  className="dark-clay-button px-2 py-0.5 rounded-lg text-rose-400 font-bold"
                >
                  Min ({fmt(decompData[minResIdx].residual)})
                </button>
              </div>
            </div>

            {/* Synchronized 4-Track SVG */}
            <div className="flex-1 min-h-0 w-full relative">
              <svg
                ref={svgRef}
                viewBox={`0 0 ${W} ${totalSvgH + PAD.b}`}
                className="w-full h-full cursor-crosshair"
                onPointerMove={onPointerMove}
                onPointerLeave={() => setHoverIndex(null)}
              >
                {panes.map((pane, pIdx) => {
                  const top = pIdx * PANE_H + PAD.t;
                  const innerH = PANE_H - PAD.t - 4;
                  const vals = pane.values;
                  const pMin = Math.min(...vals);
                  const pMax = Math.max(...vals);
                  const span = pMax - pMin || 1;
                  const sy = (v: number) => top + innerH - ((v - pMin) / span) * innerH;

                  // Build smooth path
                  const d = decompData
                    .map((pt, i) => `${i === 0 ? "M" : "L"} ${sx(pt.x).toFixed(1)} ${sy(vals[i]).toFixed(1)}`)
                    .join(" ");

                  const zeroY = pane.drawZero ? sy(0) : null;
                  const ticks = niceTicks(pMin, pMax, 2);

                  return (
                    <g key={pane.id}>
                      {/* Track background slot */}
                      <rect
                        x={PAD.l}
                        y={top}
                        width={W - PAD.l - PAD.r}
                        height={innerH}
                        fill="rgba(255, 255, 255, 0.03)"
                        rx="4"
                      />

                      {/* Zero line if applicable */}
                      {zeroY !== null && zeroY >= top && zeroY <= top + innerH && (
                        <line
                          x1={PAD.l}
                          x2={W - PAD.r}
                          y1={zeroY}
                          y2={zeroY}
                          stroke="rgba(255, 255, 255, 0.15)"
                          strokeDasharray="2,2"
                        />
                      )}

                      {/* Label & Subtitle */}
                      <text x={8} y={top + 12} fill="#ffffff" fontSize="9.5" fontWeight="bold">
                        {pane.name}
                      </text>
                      <text x={8} y={top + 22} fill="#94a3b8" fontSize="8">
                        {pane.subtitle}
                      </text>

                      {/* Y-axis Ticks */}
                      {ticks.map((tk, tIdx) => (
                        <text
                          key={tIdx}
                          x={PAD.l - 4}
                          y={sy(tk) + 3}
                          textAnchor="end"
                          fill="#64748b"
                          fontSize="7.5"
                          fontFamily="monospace"
                        >
                          {fmt(tk)}
                        </text>
                      ))}

                      {/* Series Path */}
                      <path d={d} fill="none" stroke={pane.color} strokeWidth="1.6" strokeLinejoin="round" />

                      {/* Hover Indicator Dot */}
                      {hoverIndex !== null && (
                        <circle
                          cx={sx(decompData[hoverIndex].x)}
                          cy={sy(vals[hoverIndex])}
                          r="3.5"
                          fill={pane.color}
                          stroke="#ffffff"
                          strokeWidth="1.5"
                        />
                      )}
                    </g>
                  );
                })}

                {/* Vertical Crosshair Line across all 4 tracks */}
                {hoverIndex !== null && (
                  <line
                    x1={sx(decompData[hoverIndex].x)}
                    x2={sx(decompData[hoverIndex].x)}
                    y1={PAD.t}
                    y2={totalSvgH}
                    stroke="#ffffff"
                    strokeWidth="1.2"
                    strokeDasharray="3,3"
                  />
                )}

                {/* X-axis year ticks at the bottom */}
                {xTicks.map((yr) => (
                  <text
                    key={yr}
                    x={sx(yr)}
                    y={totalSvgH + 11}
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize="8.5"
                    fontFamily="monospace"
                  >
                    {yr}
                  </text>
                ))}
              </svg>
            </div>
          </div>
        )}
      </div>

      {/* 4. SCIENTIFIC DECOMPOSITION FOOTER & INFO ABOUT THE CHARTS */}
      <div className="pt-2 border-t border-white/10 text-[11px] text-slate-300 flex items-center justify-between shrink-0">
        <span className="truncate">
          Additive Identity: <strong className="text-white font-mono">Y_t = T_t + S_t + R_t</strong> • Total Span: <strong className="text-sky-400 font-mono">{yearsSpan} Years</strong>
        </span>
        <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">
          Deseasonalized baseline T_t isolates multi-decadal secular change from annual seasonal insolation.
        </span>
      </div>
    </div>
  );
}