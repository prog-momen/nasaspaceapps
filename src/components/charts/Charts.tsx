"use client";

import React, { useRef, useState } from "react";

// Dependency-free SVG charts. Solid colors only.

const W = 800;
const PAD = { l: 52, r: 16, t: 14, b: 30 };

export interface XY {
  x: number;
  y: number;
}
export interface LineSeries {
  name: string;
  color: string;
  points: XY[];
  dashed?: boolean;
  width?: number;
}
export interface Band {
  color: string;
  points: { x: number; lo: number; hi: number }[];
}

/** "YYYY-MM" to decimal year at mid-month. */
export const dateToX = (d: string) => Number(d.slice(0, 4)) + (Number(d.slice(5, 7)) - 0.5) / 12;

function niceTicks(min: number, max: number, count = 5): number[] {
  if (min === max) return [min];
  const raw = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}

const fmtVal = (v: number) =>
  Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2);

function Frame({
  height,
  children,
  yTicks,
  xTicks,
  sx,
  sy,
  yUnit,
  onMove,
  onLeave,
  svgRef,
}: {
  height: number;
  children: React.ReactNode;
  yTicks: number[];
  xTicks: { v: number; label: string }[];
  sx: (x: number) => number;
  sy: (y: number) => number;
  yUnit: string;
  onMove?: (e: React.PointerEvent<SVGSVGElement>) => void;
  onLeave?: () => void;
  svgRef: React.RefObject<SVGSVGElement | null>;
}) {
  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${height}`}
      className="w-full h-auto touch-pan-y"
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      role="img"
    >
      {yTicks.map((t) => (
        <g key={t}>
          <line x1={PAD.l} x2={W - PAD.r} y1={sy(t)} y2={sy(t)} stroke="#1f2937" />
          <text x={PAD.l - 6} y={sy(t) + 3} textAnchor="end" fontSize="10" fill="#9ca3af">
            {fmtVal(t)}
          </text>
        </g>
      ))}
      {xTicks.map((t) => (
        <text key={t.v} x={sx(t.v)} y={height - 10} textAnchor="middle" fontSize="10" fill="#9ca3af">
          {t.label}
        </text>
      ))}
      <text x={PAD.l} y={9} fontSize="10" fill="#6b7280">
        {yUnit}
      </text>
      {children}
    </svg>
  );
}

function yearTicks(min: number, max: number) {
  return niceTicks(min, max, 6).map((v) => ({ v, label: String(Math.round(v)) }));
}

export function LineChart({
  series,
  band,
  unit,
  height = 260,
  forecastStartX,
}: {
  series: LineSeries[];
  band?: Band;
  unit: string;
  height?: number;
  /** Draws a divider where the forecast begins. */
  forecastStartX?: number;
}) {
  const ref = useRef<SVGSVGElement | null>(null);
  const [hover, setHover] = useState<number | null>(null);

  const xs = series.flatMap((s) => s.points.map((p) => p.x));
  const ys = [
    ...series.flatMap((s) => s.points.map((p) => p.y)),
    ...(band ? band.points.flatMap((p) => [p.lo, p.hi]) : []),
  ];
  if (!xs.length) return null;
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  let y0 = Math.min(...ys);
  let y1 = Math.max(...ys);
  const padY = (y1 - y0 || 1) * 0.08;
  y0 -= padY;
  y1 += padY;
  const sx = (x: number) => PAD.l + ((x - x0) / (x1 - x0 || 1)) * (W - PAD.l - PAD.r);
  const sy = (y: number) => height - PAD.b - ((y - y0) / (y1 - y0 || 1)) * (height - PAD.t - PAD.b);

  const path = (pts: XY[]) => pts.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join("");
  const bandPath = band
    ? band.points.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.hi).toFixed(1)}`).join("") +
      [...band.points].reverse().map((p) => `L${sx(p.x).toFixed(1)},${sy(p.lo).toFixed(1)}`).join("") +
      "Z"
    : null;

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    const px = ((e.clientX - rect.left) / rect.width) * W;
    setHover(x0 + ((px - PAD.l) / (W - PAD.l - PAD.r)) * (x1 - x0));
  };

  const nearest = (s: LineSeries) =>
    hover === null
      ? null
      : s.points.reduce<XY | null>((best, p) => (!best || Math.abs(p.x - hover) < Math.abs(best.x - hover) ? p : best), null);
  const hoverPts = series.map((s) => ({ s, p: nearest(s) })).filter((h) => h.p && Math.abs(h.p.x - (hover ?? 0)) < 0.2);
  const hx = hoverPts[0]?.p ? sx(hoverPts[0].p.x) : null;

  return (
    <div>
      <Frame
        height={height}
        yTicks={niceTicks(y0, y1)}
        xTicks={yearTicks(x0, x1)}
        sx={sx}
        sy={sy}
        yUnit={unit}
        onMove={onMove}
        onLeave={() => setHover(null)}
        svgRef={ref}
      >
        {bandPath && <path d={bandPath} fill={band!.color} opacity="0.22" />}
        {forecastStartX !== undefined && (
          <line x1={sx(forecastStartX)} x2={sx(forecastStartX)} y1={PAD.t} y2={height - PAD.b} stroke="#6b7280" strokeDasharray="4 4" />
        )}
        {series.map((s) => (
          <path
            key={s.name}
            d={path(s.points)}
            fill="none"
            stroke={s.color}
            strokeWidth={s.width ?? 1.6}
            strokeDasharray={s.dashed ? "6 4" : undefined}
            strokeLinejoin="round"
          />
        ))}
        {hx !== null && (
          <g>
            <line x1={hx} x2={hx} y1={PAD.t} y2={height - PAD.b} stroke="#4b5563" />
            {hoverPts.map(({ s, p }) => (
              <circle key={s.name} cx={sx(p!.x)} cy={sy(p!.y)} r="3.5" fill={s.color} />
            ))}
          </g>
        )}
      </Frame>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#9ca3af] mt-1 min-h-5">
        {series.map((s) => {
          const h = hoverPts.find((x) => x.s === s)?.p;
          return (
            <span key={s.name} className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-0.5" style={{ background: s.color }} />
              {s.name}
              {h && (
                <span className="font-mono text-[#e5e7eb]">
                  {h.x.toFixed(1)}: {fmtVal(h.y)} {unit}
                </span>
              )}
            </span>
          );
        })}
        {band && (
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 opacity-40" style={{ background: band.color }} />
            95% range
          </span>
        )}
      </div>
    </div>
  );
}

export function BarChart({
  data,
  unit,
  height = 220,
  labelFor,
  signed = false,
  color = "#3b82f6",
}: {
  data: { x: number; y: number }[];
  unit: string;
  height?: number;
  labelFor?: (x: number) => string;
  /** Color bars by sign (above/below zero). */
  signed?: boolean;
  color?: string;
}) {
  const ref = useRef<SVGSVGElement | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  if (!data.length) return null;
  const x0 = data[0].x;
  const x1 = data[data.length - 1].x;
  const ys = data.map((d) => d.y);
  let y0 = Math.min(0, ...ys);
  let y1 = Math.max(0, ...ys);
  const padY = (y1 - y0 || 1) * 0.08;
  y0 -= y0 < 0 ? padY : 0;
  y1 += padY;
  const sx = (x: number) => PAD.l + ((x - x0) / (x1 - x0 || 1)) * (W - PAD.l - PAD.r);
  const sy = (y: number) => height - PAD.b - ((y - y0) / (y1 - y0 || 1)) * (height - PAD.t - PAD.b);
  const bw = Math.max(1, ((W - PAD.l - PAD.r) / data.length) * 0.8);
  const zero = sy(0);

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const x = x0 + ((px - PAD.l) / (W - PAD.l - PAD.r)) * (x1 - x0);
    let best = 0;
    data.forEach((d, i) => {
      if (Math.abs(d.x - x) < Math.abs(data[best].x - x)) best = i;
    });
    setHover(best);
  };

  // Thin the labels so long categorical axes (e.g. 35 years) stay readable.
  const every = Math.max(1, Math.ceil(data.length / 8));
  const xTicks = labelFor
    ? data.filter((_, i) => i % every === 0).map((d) => ({ v: d.x, label: labelFor(d.x) }))
    : yearTicks(x0, x1);

  return (
    <div>
      <Frame height={height} yTicks={niceTicks(y0, y1)} xTicks={xTicks} sx={sx} sy={sy} yUnit={unit} onMove={onMove} onLeave={() => setHover(null)} svgRef={ref}>
        <line x1={PAD.l} x2={W - PAD.r} y1={zero} y2={zero} stroke="#4b5563" />
        {data.map((d, i) => (
          <rect
            key={i}
            x={sx(d.x) - bw / 2}
            y={Math.min(zero, sy(d.y))}
            width={bw}
            height={Math.abs(sy(d.y) - zero)}
            fill={signed ? (d.y >= 0 ? "#f59e0b" : "#3b82f6") : color}
            opacity={hover === i ? 1 : 0.85}
          />
        ))}
      </Frame>
      <div className="text-xs text-[#9ca3af] mt-1 min-h-5 font-mono">
        {hover !== null && `${labelFor ? labelFor(data[hover].x) : data[hover].x.toFixed(1)}: ${fmtVal(data[hover].y)} ${unit}`}
      </div>
    </div>
  );
}
