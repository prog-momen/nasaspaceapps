"use client";

import React, { Suspense, useState } from "react";
import { useAsync } from "../lib/useAsync";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import PageFrame, { Card, ErrorBox, Loading, Stat, VERDICT, fmt, fmtP, signed } from "./PageFrame";
import AnalysisControls from "./AnalysisControls";
import { BarChart, LineChart, dateToX } from "./charts/Charts";
import { fetchAnalysis, parseSelection, selectionToParams, type Selection } from "../lib/api-client";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const HORIZONS = [1, 2, 5, 10];

function Explain({ what, why, inference }: { what: string; why: string; inference: string }) {
  const rows = [
    ["What it shows", what],
    ["Why it matters", why],
    ["What to conclude", inference],
  ];
  return (
    <dl className="mt-3 grid gap-2 sm:grid-cols-3 text-xs">
      {rows.map(([k, v]) => (
        <div key={k} className="bg-[#0b0f19] border border-[#1f2937] rounded p-2.5">
          <dt className="text-[#60a5fa] font-semibold mb-1">{k}</dt>
          <dd className="text-[#cbd5e1] leading-relaxed">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function Dashboard({ sel }: { sel: Selection }) {
  const router = useRouter();
  const [horizon, setHorizon] = useState(5);
  const [editing, setEditing] = useState(false);
  const { data, error, retry: load } = useAsync(() => fetchAnalysis(sel), selectionToParams(sel).toString());

  const title = `${sel.name}`;
  if (error) {
    return (
      <PageFrame title={title} subtitle="Dashboard">
        <ErrorBox message={error} onRetry={load} />
      </PageFrame>
    );
  }
  if (!data) {
    return (
      <PageFrame title={title} subtitle="Dashboard">
        <Loading text="Fetching NASA satellite and model data and running the trend analysis. This can take a few seconds." />
      </PageFrame>
    );
  }

  const { trend: t, variable: v, region } = data;
  const v10 = t.ols.slopePerYear * 10;
  const verdict = VERDICT[t.verdict];
  const explain = Object.fromEntries(data.charts.map((c) => [c.id, c]));
  const chart = (id: string, body: React.ReactNode) => (
    <Card title={explain[id]?.title}>
      {body}
      {explain[id] && <Explain what={explain[id].what} why={explain[id].why} inference={explain[id].inference} />}
    </Card>
  );

  return (
    <PageFrame
      title={`${region.name}${region.country && region.country !== region.name ? `, ${region.country}` : ""}`}
      subtitle={`${v.name} - ${t.period.start} to ${t.period.end} - ${region.lat.toFixed(1)}, ${region.lon.toFixed(1)}`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className={`text-xs px-2.5 py-1 rounded border ${verdict.cls}`}>{verdict.label}</span>
        <button onClick={() => setEditing((e) => !e)} className="text-xs px-3 py-1.5 rounded border border-[#374151] bg-[#111827] hover:bg-[#1f2937] text-[#cbd5e1]">
          {editing ? "Close" : "Change variable or period"}
        </button>
      </div>

      {editing && (
        <Card>
          <AnalysisControls
            lat={sel.lat}
            lon={sel.lon}
            name={sel.name}
            initial={sel}
            submitLabel="Update analysis"
            onApply={(s) => {
              setEditing(false);
              router.replace(`/dashboard?${selectionToParams(s)}`);
            }}
          />
        </Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Trend per decade" value={`${signed(v10)} ${v.unit}`} hint={`${t.direction}`} />
        <Stat label="Total change" value={`${signed(t.totalChange)} ${v.unit}`} hint={t.percentChange === null ? `over ${t.period.years} years` : `${signed(t.percentChange, 1)}% over ${t.period.years} years`} />
        <Stat label="Average" value={`${fmt(t.mean)} ${v.unit}`} hint={`std dev ${fmt(t.stdDev)}`} />
        <Stat label="Range" value={`${fmt(t.min.value)} to ${fmt(t.max.value)}`} hint={`${t.min.date} / ${t.max.date}`} />
      </div>

      <Card title="Summary">
        <ul className="flex flex-col gap-2 text-sm text-[#d1d5db] leading-relaxed">
          {data.summary.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
        <p className="text-xs text-[#6b7280] mt-3">
          Source: {data.source.provider}. {data.source.note}
        </p>
      </Card>

      {chart(
        "timeseries",
        <LineChart
          unit={v.unit}
          series={[
            { name: "Monthly value", color: "#60a5fa", points: data.series.map((s) => ({ x: dateToX(s.date), y: s.value })) },
            { name: "Linear trend", color: "#f59e0b", dashed: true, width: 2.2, points: data.series.map((s) => ({ x: dateToX(s.date), y: s.trend })) },
          ]}
        />,
      )}
      {chart("anomalies", <BarChart signed unit={v.unit} data={data.series.map((s) => ({ x: dateToX(s.date), y: s.anomaly }))} />)}
      {chart("annual", <BarChart unit={v.unit} labelFor={(x) => String(Math.round(x))} data={t.annual.map((a) => ({ x: a.year, y: a.mean }))} />)}
      {chart("seasonal", <BarChart unit={v.unit} labelFor={(x) => MONTHS[x - 1]} data={t.seasonalClimatology.map((y, i) => ({ x: i + 1, y }))} />)}

      <Card title={explain.significance?.title ?? "Significance tests"}>
        <div className="grid gap-3 sm:grid-cols-2 text-xs">
          <table className="w-full">
            <caption className="text-left text-[#60a5fa] font-semibold mb-1">Linear regression (t-test)</caption>
            <tbody className="text-[#cbd5e1]">
              {[
                ["Slope", `${signed(t.ols.slopePerYear, 3)} ${v.unit}/year`],
                ["95% interval", `${fmt(t.ols.ci95[0], 3)} to ${fmt(t.ols.ci95[1], 3)}`],
                ["p-value", fmtP(t.ols.pValue)],
                ["R squared", t.ols.r2.toFixed(3)],
                ["Effective samples", `${Math.round(t.ols.effectiveN)} of ${t.ols.n}`],
              ].map(([k, val]) => (
                <tr key={k} className="border-t border-[#1f2937]">
                  <td className="py-1.5 text-[#9ca3af]">{k}</td>
                  <td className="py-1.5 text-right font-mono">{val}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="w-full">
            <caption className="text-left text-[#60a5fa] font-semibold mb-1">Mann-Kendall (annual means)</caption>
            <tbody className="text-[#cbd5e1]">
              {[
                ["Sen's slope", `${signed(t.mannKendall.senSlopePerYear, 3)} ${v.unit}/year`],
                ["95% interval", `${fmt(t.mannKendall.senCi95[0], 3)} to ${fmt(t.mannKendall.senCi95[1], 3)}`],
                ["p-value", fmtP(t.mannKendall.pValue)],
                ["Kendall tau", t.mannKendall.tau.toFixed(3)],
                ["Years used", String(t.mannKendall.n)],
              ].map(([k, val]) => (
                <tr key={k} className="border-t border-[#1f2937]">
                  <td className="py-1.5 text-[#9ca3af]">{k}</td>
                  <td className="py-1.5 text-right font-mono">{val}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {explain.significance && <Explain what={explain.significance.what} why={explain.significance.why} inference={explain.significance.inference} />}
      </Card>

      <Card title="Forecast this trend">
        <p className="text-sm text-[#9ca3af] mb-3">Choose how far ahead to project the {v.name.toLowerCase()} for {region.name}.</p>
        <div className="flex flex-wrap items-center gap-2">
          {HORIZONS.map((h) => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`px-3 py-1.5 text-xs rounded border ${horizon === h ? "bg-[#2563eb] border-[#2563eb] text-white" : "bg-[#0b0f19] border-[#1f2937] text-[#cbd5e1] hover:bg-[#1f2937]"}`}
            >
              {h} year{h > 1 ? "s" : ""}
            </button>
          ))}
          <Link
            href={`/forecast?${selectionToParams(sel)}&horizon=${horizon}`}
            className="ml-auto px-4 py-1.5 text-xs font-semibold rounded bg-[#22c55e] hover:bg-[#16a34a] text-white"
          >
            Forecast
          </Link>
        </div>
      </Card>
    </PageFrame>
  );
}

function Inner() {
  const sel = parseSelection(useSearchParams());
  if (!sel) {
    return (
      <PageFrame title="Dashboard">
        <ErrorBox message="No region selected. Go back to the globe and choose a country first." />
      </PageFrame>
    );
  }
  return <Dashboard sel={sel} />;
}

export default function DashboardView() {
  return (
    <Suspense fallback={<PageFrame title="Dashboard"><Loading text="Loading..." /></PageFrame>}>
      <Inner />
    </Suspense>
  );
}
