"use client";

import React from "react";
import type { Artifact } from "@/lib/assistant/types";

// Small dependency-free SVG/HTML renderers for the AI service's artifacts.

const W = 420;
const H = 150;
const P = { l: 40, r: 8, t: 8, b: 20 };
const C_LINE = "#34d399";
const C_BAR = "#60a5fa";
const C_HOT = "#f87171";
const C_FC = "#fbbf24";
const GRID = "rgba(255,255,255,0.12)";
const MUTED = "#a1a1aa";

type Num = number | null | undefined;
const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2));
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const nums = (v: unknown): Num[] => arr(v).map((x) => (isNum(x) ? x : null));

function scaleOf(values: number[], zero = false) {
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (zero) lo = Math.min(0, lo);
  if (lo === hi) {
    lo -= 1;
    hi += 1;
  }
  const pad = (hi - lo) * 0.06;
  return { lo: lo - pad, hi: hi + pad };
}

function Frame({ lo, hi, xLabels, children }: { lo: number; hi: number; xLabels: string[]; children: React.ReactNode }) {
  const ph = H - P.t - P.b;
  const pw = W - P.l - P.r;
  const Y = (v: number) => P.t + (1 - (v - lo) / (hi - lo)) * ph;
  const n = xLabels.length;
  const ticks = Math.min(5, n);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img">
      {[0, 1, 2, 3].map((k) => {
        const v = lo + ((hi - lo) * k) / 3;
        return (
          <g key={k}>
            <line x1={P.l} x2={W - P.r} y1={Y(v)} y2={Y(v)} stroke={GRID} />
            <text x={P.l - 4} y={Y(v) + 3} textAnchor="end" fontSize="9" fill={MUTED}>
              {fmt(v)}
            </text>
          </g>
        );
      })}
      {Array.from({ length: ticks }, (_, k) => {
        const i = ticks === 1 ? 0 : Math.round((k * (n - 1)) / (ticks - 1));
        const x = P.l + (n === 1 ? pw / 2 : (i / (n - 1)) * pw);
        return (
          <text key={k} x={Math.min(Math.max(x, P.l + 12), W - 18)} y={H - 6} textAnchor="middle" fontSize="9" fill={MUTED}>
            {String(xLabels[i]).slice(0, 10)}
          </text>
        );
      })}
      {children}
    </svg>
  );
}

function path(ys: Num[], X: (i: number) => number, Y: (v: number) => number) {
  let d = "";
  let pen = false;
  ys.forEach((v, i) => {
    if (!isNum(v)) {
      pen = false;
      return;
    }
    d += `${pen ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

function SeriesChart({ x, s, trend, title }: { x: string[]; s: Record<string, unknown>; trend?: { y?: unknown; label?: string } | null; title: string }) {
  const ys = nums(s.y);
  const ty = trend ? nums(trend.y) : [];
  const vals = [...ys, ...ty].filter(isNum);
  if (!vals.length) return <div className="text-[10px] text-[#71717a]">No numeric values</div>;
  const bar = s.kind === "bar";
  const { lo, hi } = scaleOf(vals, bar);
  const n = x.length || ys.length;
  const pw = W - P.l - P.r;
  const ph = H - P.t - P.b;
  const X = (i: number) => P.l + (n <= 1 ? pw / 2 : (i / (n - 1)) * pw);
  const Y = (v: number) => P.t + (1 - (v - lo) / (hi - lo)) * ph;
  const bw = Math.max(1, Math.min(10, (pw / Math.max(n, 1)) * 0.7));
  return (
    <div>
      <div className="text-[10px] text-[#a1a1aa] mb-0.5">
        {String(s.name ?? "")}
        {s.unit ? ` (${String(s.unit)})` : ""}
      </div>
      <Frame lo={lo} hi={hi} xLabels={x.length ? x : ys.map((_, i) => String(i))}>
        <title>{title}</title>
        {bar ? (
          ys.map((v, i) =>
            isNum(v) ? (
              <rect key={i} x={X(i) - bw / 2} y={Math.min(Y(0), Y(v))} width={bw} height={Math.abs(Y(v) - Y(0))} fill={C_BAR} />
            ) : null,
          )
        ) : (
          <>
            <path d={path(ys, X, Y)} fill="none" stroke={C_LINE} strokeWidth="1.6" />
            {n <= 50 && ys.map((v, i) => (isNum(v) ? <circle key={i} cx={X(i)} cy={Y(v)} r="2" fill={C_LINE} /> : null))}
          </>
        )}
        {ty.length >= 2 && isNum(ty[0]) && isNum(ty[1]) && (
          <line x1={X(0)} y1={Y(ty[0])} x2={X(n - 1)} y2={Y(ty[1])} stroke={C_HOT} strokeWidth="1.6" strokeDasharray="5 3" />
        )}
      </Frame>
    </div>
  );
}

function LineChart({ a }: { a: Artifact }) {
  const x = arr(a.x).map(String);
  const series = arr(a.series) as Record<string, unknown>[];
  const trend = (a.trend_line as { y?: unknown; label?: string } | undefined) ?? null;
  return (
    <div className="space-y-2">
      {series.map((s, i) => (
        <SeriesChart key={i} x={x} s={s} title={a.title ?? ""} trend={series.length === 1 ? trend : null} />
      ))}
      {trend?.label && <div className="text-[10px] text-[#f87171]">- - - {trend.label}</div>}
    </div>
  );
}

const MAX_FORECAST_ROWS = 12;
const range = (l: Num, u: Num) => (isNum(l) && isNum(u) ? `${fmt(l)} – ${fmt(u)}` : "");

/** The forecast chart draws its own month-by-month table, so the service's sampled "selected values" table is redundant beside it. */
export function visibleInline(inline: Artifact[]): Artifact[] {
  if (!inline.some((a) => a.type === "forecast_chart")) return inline;
  return inline.filter((a) => !(a.type === "table" && a.compact === true));
}

function ForecastChart({ a }: { a: Artifact }) {
  const [hover, setHover] = React.useState<number | null>(null);
  const h = (a.history ?? {}) as { x?: unknown; y?: unknown };
  const f = (a.forecast ?? {}) as Record<string, unknown>;
  // Keep the last 3 years of history so the forecast months are wide enough to read and hover.
  const HIST = 36;
  const hx = arr(h.x).map(String).slice(-HIST);
  const hy = nums(h.y).slice(-HIST);
  const fx = arr(f.x).map(String);
  const fy = nums(f.y);
  const lo95 = nums(f.lo95);
  const hi95 = nums(f.hi95);
  const lo80 = nums(f.lo80);
  const hi80 = nums(f.hi80);
  const all = [...hy, ...fy, ...lo95, ...hi95].filter(isNum);
  if (!all.length) return null;
  const { lo, hi } = scaleOf(all);
  const n = hx.length + fx.length;
  const off = hx.length;
  const pw = W - P.l - P.r;
  const ph = H - P.t - P.b;
  const X = (i: number) => P.l + (n <= 1 ? pw / 2 : (i / (n - 1)) * pw);
  const Y = (v: number) => P.t + (1 - (v - lo) / (hi - lo)) * ph;
  const band = (l: Num[], u: Num[], color: string, op: number) => {
    const top = u.map((v, i) => (isNum(v) ? `${X(off + i)},${Y(v)}` : null)).filter(Boolean);
    const bot = l
      .map((v, i) => (isNum(v) ? `${X(off + i)},${Y(v)}` : null))
      .filter(Boolean)
      .reverse();
    return top.length ? <polygon points={[...top, ...bot].join(" ")} fill={color} opacity={op} /> : null;
  };
  const fpath = fy
    .map((v, i) => (isNum(v) ? `${i === 0 || !isNum(fy[i - 1]) ? "M" : "L"}${X(off + i).toFixed(1)} ${Y(v).toFixed(1)}` : ""))
    .join("");
  const unit = a.unit ? String(a.unit) : "";
  // Pointer position -> nearest month (history or forecast), in viewBox units so it works at any rendered width.
  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    if (!r.width || n <= 1) return;
    const vx = ((e.clientX - r.left) / r.width) * W;
    setHover(Math.max(0, Math.min(n - 1, Math.round(((vx - P.l) / pw) * (n - 1)))));
  };
  const isFc = hover !== null && hover >= off;
  const hv = hover === null ? null : isFc ? fy[hover - off] : hy[hover];
  const hd = hover === null ? "" : (isFc ? fx[hover - off] : hx[hover]) ?? "";
  // Months between the last NASA data month and today are forecast too ("gap" months); the requested span starts at the current month.
  const gap = arr(f.gap).map(Boolean);
  const nGap = gap.filter(Boolean).length;
  const shown = Math.min(fx.length, nGap + MAX_FORECAST_ROWS);
  const firstReq = fx.find((_, i) => !gap[i]);
  const asked = isNum(a.requested_months) ? a.requested_months : null;
  return (
    <div>
      <div className="relative touch-pan-y" onPointerMove={onMove} onPointerDown={onMove} onPointerLeave={() => setHover(null)}>
        <Frame lo={lo} hi={hi} xLabels={[...hx, ...fx].map((d) => d.slice(0, 7))}>
          {band(lo95, hi95, C_FC, 0.15)}
          {band(lo80, hi80, C_FC, 0.28)}
          <path d={path(hy, X, Y)} fill="none" stroke={C_LINE} strokeWidth="1.5" />
          <path d={fpath} fill="none" stroke={C_FC} strokeWidth="1.8" strokeDasharray="5 3" />
          {fy.map((v, i) => (isNum(v) ? <circle key={i} cx={X(off + i)} cy={Y(v)} r="1.8" fill={C_FC} /> : null))}
          <line x1={X(off - 0.5)} x2={X(off - 0.5)} y1={P.t} y2={P.t + ph} stroke={MUTED} strokeDasharray="2 3" />
          {hover !== null && isNum(hv) && (
            <>
              <line x1={X(hover)} x2={X(hover)} y1={P.t} y2={P.t + ph} stroke="#ffffff" strokeOpacity="0.45" />
              <circle cx={X(hover)} cy={Y(hv)} r="3.2" fill={isFc ? C_FC : C_LINE} stroke="#000000" strokeWidth="1" />
            </>
          )}
        </Frame>
        {hover !== null && isNum(hv) && (
          <div
            className="pointer-events-none absolute top-1 px-2 py-1 rounded-md bg-black/85 border border-white/15 text-[10px] leading-tight text-[#f4f4f5] whitespace-nowrap"
            style={X(hover) > W / 2 ? { right: `${100 - (X(hover) / W) * 100 + 1.5}%` } : { left: `${(X(hover) / W) * 100 + 1.5}%` }}
          >
            <div className="font-semibold">
              {hd.slice(0, 7)} · {isFc ? "forecast" : "observed"}
            </div>
            <div style={{ color: isFc ? C_FC : C_LINE }}>
              {fmt(hv)} {unit}
            </div>
            {isFc && range(lo80[hover - off], hi80[hover - off]) && <div className="text-[#a1a1aa]">80%: {range(lo80[hover - off], hi80[hover - off])}</div>}
            {isFc && range(lo95[hover - off], hi95[hover - off]) && <div className="text-[#a1a1aa]">95%: {range(lo95[hover - off], hi95[hover - off])}</div>}
          </div>
        )}
      </div>
      <div className="text-[10px] text-[#a1a1aa]">
        <span style={{ color: C_LINE }}>--</span> history · <span style={{ color: C_FC }}>- -</span> forecast · shaded 80% / 95% interval
        {unit ? ` · ${unit}` : ""}
        {a.cutoff ? ` · cutoff ${String(a.cutoff).slice(0, 7)}` : ""} · hover or tap the chart to read a month
      </div>
      {shown > 0 && (asked !== null || nGap > 0) && (
        <div className="mt-2 text-[11px] leading-snug text-[#d4d4d8]">
          {asked !== null && firstReq && (
            <span>
              <b className="text-[#f4f4f5]">Asked:</b> {asked} month{asked === 1 ? "" : "s"} from today
              {a.issue_date ? ` (${String(a.issue_date)})` : ""}: {firstReq.slice(0, 7)} → {fx[fx.length - 1].slice(0, 7)}.{" "}
            </span>
          )}
          {nGap > 0 && (
            <span>
              <b className="text-sky-300">+ {nGap} missing month{nGap === 1 ? "" : "s"}:</b> NASA data end {a.cutoff ? String(a.cutoff).slice(0, 7) : "earlier"}, so the month
              {nGap === 1 ? "" : "s"} before today {nGap === 1 ? "is" : "are"} forecast as well.
            </span>
          )}
        </div>
      )}
      {shown > 0 && (
        <div className="mt-2 overflow-x-auto rounded-lg border border-white/10">
          <table className="w-full text-[11px] text-left">
            <thead className="bg-white/5 text-[#a1a1aa]">
              <tr>
                <th className="px-2 py-1 font-semibold whitespace-nowrap">Month</th>
                <th className="px-2 py-1 font-semibold whitespace-nowrap">Forecast{unit ? ` (${unit})` : ""}</th>
                <th className="px-2 py-1 font-semibold whitespace-nowrap">80% interval</th>
                <th className="px-2 py-1 font-semibold whitespace-nowrap">95% interval</th>
                <th className="px-2 py-1 font-semibold whitespace-nowrap">Part</th>
              </tr>
            </thead>
            <tbody>
              {fx.slice(0, shown).map((d, i) => (
                <tr
                  key={d}
                  className={`border-t border-white/5 ${hover === off + i ? "bg-amber-400/15" : ""}`}
                  onPointerEnter={() => setHover(off + i)}
                  onPointerLeave={() => setHover(null)}
                >
                  <td className="px-2 py-1 whitespace-nowrap font-mono text-[#f4f4f5]">{d.slice(0, 7)}</td>
                  <td className="px-2 py-1 whitespace-nowrap font-semibold" style={{ color: C_FC }}>
                    {isNum(fy[i]) ? fmt(fy[i] as number) : ""}
                  </td>
                  <td className="px-2 py-1 whitespace-nowrap text-[#d4d4d8]">{range(lo80[i], hi80[i])}</td>
                  <td className="px-2 py-1 whitespace-nowrap text-[#a1a1aa]">{range(lo95[i], hi95[i])}</td>
                  <td className="px-2 py-1 whitespace-nowrap">
                    {gap[i] ? (
                      <span className="px-1.5 py-0.5 rounded bg-sky-400/15 text-sky-300 border border-sky-400/30">missing data (before today)</span>
                    ) : (
                      <span className="text-[#a1a1aa]">requested</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {fx.length > shown && (
            <div className="px-2 py-1 text-[10px] text-[#71717a]">
              First {shown} of {fx.length} forecast months shown; hover the chart or open Details for the rest.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EnsembleChart({ a }: { a: Artifact }) {
  const d = (a.daily ?? {}) as Record<string, unknown>;
  const dates = arr(a.dates).map(String);
  const med = nums(d.median);
  const p10 = nums(d.p10);
  const p90 = nums(d.p90);
  const p25 = nums(d.p25);
  const p75 = nums(d.p75);
  const all = [...med, ...p10, ...p90].filter(isNum);
  if (!all.length) return null;
  const { lo, hi } = scaleOf(all);
  const n = dates.length;
  const pw = W - P.l - P.r;
  const ph = H - P.t - P.b;
  const X = (i: number) => P.l + (n <= 1 ? pw / 2 : (i / (n - 1)) * pw);
  const Y = (v: number) => P.t + (1 - (v - lo) / (hi - lo)) * ph;
  const band = (l: Num[], u: Num[], op: number) => {
    const top = u.map((v, i) => (isNum(v) ? `${X(i)},${Y(v)}` : null)).filter(Boolean);
    const bot = l
      .map((v, i) => (isNum(v) ? `${X(i)},${Y(v)}` : null))
      .filter(Boolean)
      .reverse();
    return <polygon points={[...top, ...bot].join(" ")} fill={C_LINE} opacity={op} />;
  };
  return (
    <div>
      <Frame lo={lo} hi={hi} xLabels={dates.map((x) => x.slice(5, 10))}>
        {band(p10, p90, 0.15)}
        {band(p25, p75, 0.3)}
        <path d={path(med, X, Y)} fill="none" stroke={C_LINE} strokeWidth="1.8" />
      </Frame>
      <div className="text-[10px] text-[#a1a1aa]">
        line = median across members; dark band = p25-p75, light band = p10-p90 (spread, not a calibrated uncertainty){a.unit ? ` · ${String(a.unit)}` : ""}
      </div>
    </div>
  );
}

function DataTable({ a }: { a: Artifact }) {
  const cols = arr(a.columns).map(String);
  const rows = arr(a.rows).slice(0, 100) as unknown[][];
  return (
    <div className="overflow-x-auto max-h-56 overflow-y-auto rounded-lg border border-white/10">
      <table className="w-full text-[10px] text-left">
        <thead className="bg-white/5 text-[#a1a1aa] sticky top-0">
          <tr>
            {cols.map((c, i) => (
              <th key={i} className="px-2 py-1 font-semibold whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-white/5">
              {arr(r).map((v, j) => (
                <td key={j} className="px-2 py-1 whitespace-nowrap text-[#f4f4f5]">
                  {v === null || v === undefined ? "" : String(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {arr(a.rows).length > 100 && <div className="px-2 py-1 text-[10px] text-[#71717a]">100 / {arr(a.rows).length} rows shown</div>}
    </div>
  );
}

function Fallback({ a }: { a: Artifact }) {
  const labels: Record<string, string> = {
    map_points: `${arr(a.points).length} map points (map view is not shown here)`,
    map_polygons: "Map polygons (map view is not shown here)",
    wms_overlay: "Map overlay layer (map view is not shown here)",
    tile_overlay: "Map overlay layer (map view is not shown here)",
    scenes: `${arr(a.scenes).length} satellite scenes found`,
    category_strip: "Category strip",
  };
  if (a.type === "category_strip") {
    const cells = arr(a.cells) as { label?: string; text?: string; color?: string }[];
    return (
      <div className="flex flex-wrap gap-1">
        {cells.map((c, i) => (
          <div key={i} className="px-1.5 py-1 rounded text-[10px] text-black" style={{ background: c.color || "#ddd" }} title={c.text}>
            <b>{c.label}</b> {c.text}
          </div>
        ))}
      </div>
    );
  }
  return <div className="text-[10px] text-[#a1a1aa]">{labels[a.type] ?? `Artifact: ${a.type}`}</div>;
}

export function ArtifactView({ artifact }: { artifact: Artifact }) {
  let body: React.ReactNode;
  switch (artifact.type) {
    case "line_chart":
      body = <LineChart a={artifact} />;
      break;
    case "forecast_chart":
      body = <ForecastChart a={artifact} />;
      break;
    case "ensemble_chart":
      body = <EnsembleChart a={artifact} />;
      break;
    case "table":
      body = <DataTable a={artifact} />;
      break;
    default:
      body = <Fallback a={artifact} />;
  }
  return (
    <figure className="my-2 rounded-xl border border-white/10 bg-black/30 p-2.5">
      {artifact.title && (
        <figcaption dir="auto" className="text-[11px] font-semibold text-[#f4f4f5] mb-1.5">
          {artifact.title}
        </figcaption>
      )}
      {body}
      {artifact.note && (
        <div dir="auto" className="mt-1 text-[10px] text-[#71717a]">
          {artifact.note}
        </div>
      )}
    </figure>
  );
}
