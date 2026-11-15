"use client";

import React, { Suspense } from "react";
import { useAsync } from "../lib/useAsync";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import PageFrame, { Card, ErrorBox, Loading, Stat, VERDICT, fmt, signed } from "./PageFrame";
import SourcesNote from "./SourcesNote";
import { LineChart, dateToX } from "./charts/Charts";
import {
  DEFAULT_VARIABLE,
  defaultEnd,
  defaultStart,
  fetchForecast,
  parseSelection,
  selectionToParams,
  type Selection,
} from "../lib/api-client";
import { COUNTRIES } from "../data/countries";

/** Three confidence zones for a forecast horizon, based on what the backtest actually covers. */
function ConfidenceZones({ horizon, testedMonths, beats }: { horizon: number; testedMonths: number; beats: boolean }) {
  const testedYears = Math.max(1, Math.floor(testedMonths / 12));
  const active = horizon <= testedYears ? 0 : horizon <= 10 ? 1 : 2;
  const zones = [
    {
      range: `up to ${testedYears} year${testedYears === 1 ? "" : "s"}`,
      title: "Tested",
      text: beats
        ? "Checked against the last real months and it did better than the seasonal average. Use the 95% band as the confidence range."
        : "Checked against the last real months, but it was not better than the seasonal average here, so treat it as indicative.",
      cls: "border-emerald-500/50 bg-emerald-500/10",
    },
    {
      range: `${testedYears} to 10 years`,
      title: "Extrapolation",
      text: "Assumes the historical trend simply continues. Not validated: the band widens and the result is a scenario, not a prediction.",
      cls: "border-amber-500/50 bg-amber-500/10",
    },
    {
      range: "over 10 years",
      title: "Computation only",
      text: "Mathematically extended. No evidence supports it and the confidence is far lower than in the first zone. Do not read it as a forecast.",
      cls: "border-red-500/50 bg-red-500/10",
    },
  ];
  return (
    <div role="group" aria-label="Confidence by forecast horizon" className="grid grid-cols-1 gap-2 sm:grid-cols-3">
      {zones.map((z, i) => (
        <div key={z.title} className={`rounded-xl border p-3 text-xs leading-relaxed ${i === active ? z.cls : "border-white/10 bg-black/20 opacity-60"}`}>
          <div className="flex items-center justify-between gap-2">
            <b className="text-white">{z.title}</b>
            <span className="text-[#a1a1aa]">{z.range}</span>
          </div>
          <p className="mt-1 text-[#d4d4d8]">{z.text}</p>
          {i === active && <p className="mt-1 font-semibold text-white">Your selection ({horizon} year{horizon === 1 ? "" : "s"}) is here.</p>}
        </div>
      ))}
    </div>
  );
}

function Forecast({ sel, horizon }: { sel: Selection; horizon: number }) {
  const { data, error, retry: load } = useAsync(() => fetchForecast(sel, horizon), `${selectionToParams(sel)}&h=${horizon}`);

  if (error) {
    return (
      <PageFrame title={sel.name} subtitle="Forecast">
        <ErrorBox message={error} onRetry={load} />
      </PageFrame>
    );
  }
  if (!data) {
    return (
      <PageFrame title={sel.name} subtitle="Forecast">
        <Loading text="Building the forecast from the historical record..." />
      </PageFrame>
    );
  }

  const { forecast: f, variable: v, region, trend } = data;
  const verdict = VERDICT[trend.verdict];
  const hist = data.historical.map(([d, y]) => ({ x: dateToX(d), y }));
  const fut = f.forecast.map((p) => ({ x: dateToX(p.date), y: p.value }));
  // Connect the two lines visually at the boundary.
  const futLine = hist.length ? [hist[hist.length - 1], ...fut] : fut;

  return (
    <PageFrame
      title={`${region.name} - ${horizon} year forecast`}
      subtitle={`${v.name} - history ${data.query.start} to ${data.query.end}`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className={`text-xs px-2.5 py-1 rounded border ${verdict.cls}`}>Historical trend: {verdict.label.toLowerCase()}</span>
        <Link href={`/dashboard?${selectionToParams(sel)}`} className="text-xs px-3 py-1.5 rounded border border-[#374151] bg-[#111827] hover:bg-[#1f2937] text-[#cbd5e1]">
          Back to dashboard
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Forecast horizon">
        <span className="text-xs text-[#9ca3af] mr-1">Horizon (years):</span>
        {[1, 2, 5, 10, 20].map((h) => {
          const p = new URLSearchParams(selectionToParams(sel));
          p.set("horizon", String(h));
          const active = h === horizon;
          return (
            <Link
              key={h}
              href={`/forecast?${p}`}
              aria-current={active ? "page" : undefined}
              className={`px-3 py-1.5 text-xs rounded-lg border font-semibold ${
                active ? "bg-amber-500 text-black border-amber-300" : "bg-[#111827] text-[#cbd5e1] border-[#374151] hover:bg-[#1f2937]"
              }`}
            >
              {h}
            </Link>
          );
        })}
        <span className="text-[11px] text-[#6b7280] ml-1">A {horizon}-year projection extends the trend; it is not a climate model run.</span>
      </div>

      {f.forecast.length > 0 && (
        <p className="text-xs leading-relaxed text-[#d4d4d8]">
          <b className="text-white">Asked:</b> {horizon} year{horizon === 1 ? "" : "s"} from today ({f.issueDate}):{" "}
          {f.forecast[f.gapMonths.length]?.date ?? f.forecast[0].date} → {f.forecast[f.forecast.length - 1].date}.
          {f.gapMonths.length > 0 && (
            <>
              {" "}
              <b className="text-sky-300">+ {f.gapMonths.length} missing month{f.gapMonths.length === 1 ? "" : "s"}</b> ({f.gapMonths[0]}
              {f.gapMonths.length > 1 ? ` to ${f.gapMonths[f.gapMonths.length - 1]}` : ""}): NASA data end {data.query.end}, so the months before today are forecast as well.
            </>
          )}
        </p>
      )}

      <ConfidenceZones horizon={horizon} testedMonths={f.backtest?.holdoutMonths ?? 0} beats={f.backtest?.beatsBaseline ?? false} />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Last 2 years average" value={`${fmt(f.expectedChange.fromLastYearMean)} ${v.unit}`} />
        <Stat label={`Projected final year`} value={`${fmt(f.expectedChange.toFinalYearMean)} ${v.unit}`} />
        <Stat
          label="Expected change"
          value={`${signed(f.expectedChange.absolute)} ${v.unit}`}
          hint={f.expectedChange.percent === null ? undefined : `${signed(f.expectedChange.percent, 1)}%`}
        />
        <Stat label="Trend rate" value={`${signed(trend.slopePerYear * 10)} ${v.unit}`} hint="per decade" />
      </div>

      <Card title="Historical data and forecast">
        <LineChart
          unit={v.unit}
          height={300}
          forecastStartX={fut[0]?.x}
          series={[
            { name: "Historical", color: "#60a5fa", points: hist },
            { name: "Forecast", color: "#f59e0b", width: 2.2, points: futLine },
          ]}
          band={{ color: "#f59e0b", points: f.forecast.map((p) => ({ x: dateToX(p.date), lo: p.lower, hi: p.upper })) }}
        />
        <p className="text-xs text-[#9ca3af] mt-3">The dashed vertical line marks where observations end and the forecast begins.</p>
      </Card>

      <Card title="Summary">
        <ul className="flex flex-col gap-2 text-sm text-[#d1d5db] leading-relaxed">
          {data.summary.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      </Card>

      <Card title="Yearly projection">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[#9ca3af]">
              <th className="py-1.5 font-medium">Year</th>
              <th className="py-1.5 font-medium text-right">Projected average</th>
              <th className="py-1.5 font-medium text-right">Lower</th>
              <th className="py-1.5 font-medium text-right">Upper</th>
            </tr>
          </thead>
          <tbody className="text-[#cbd5e1] font-mono">
            {f.annualForecast.map((a) => (
              <tr key={a.year} className="border-t border-[#1f2937]">
                <td className="py-1.5">{a.year}</td>
                <td className="py-1.5 text-right">{fmt(a.mean)} {v.unit}</td>
                <td className="py-1.5 text-right">{fmt(a.lower)}</td>
                <td className="py-1.5 text-right">{fmt(a.upper)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="How the forecast works">
        <p className="text-sm text-[#d1d5db] leading-relaxed">{f.description}</p>
        {f.backtest && (
          <p className="text-xs text-[#9ca3af] mt-3">
            Accuracy check on the most recent {f.backtest.holdoutMonths} months: average error {fmt(f.backtest.modelMae)} {v.unit} with the trend,
            {" "}{fmt(f.backtest.baselineMae)} {v.unit} using the seasonal average alone.
          </p>
        )}
        <ul className="list-disc pl-5 mt-3 text-xs text-[#9ca3af] flex flex-col gap-1">
          {f.caveats.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </Card>
      <SourcesNote
        labels={{ title: "Sources", relies: "Relies on", used: "Used in this forecast" }}
        relies={[
          "NASA POWER monthly point API (MERRA-2 / CERES)",
          "linear trend on deseasonalised anomalies + repeating seasonal cycle, 95% prediction interval",
          "hold-out backtest of the last months against a seasonal-average baseline",
        ]}
        used={[
          `NASA POWER ${v.source_model ?? "MERRA-2"} 0.5° cell (${region.lat.toFixed(2)}, ${region.lon.toFixed(2)})`,
          `history ${data.query.start}–${data.query.end}, ${f.forecast.length} forecast months, issued ${f.issueDate}`,
          f.backtest ? `backtest on ${f.backtest.holdoutMonths} months: model ${f.backtest.beatsBaseline ? "beat" : "did not beat"} the seasonal baseline` : "backtest: not enough history",
        ]}
        links={[
          {
            label: "NASA POWER data request for this place (JSON)",
            url: `https://power.larc.nasa.gov/api/temporal/monthly/point?${new URLSearchParams({
              parameters: v.provider_param,
              community: "AG",
              latitude: String(region.lat),
              longitude: String(region.lon),
              start: String(data.query.start),
              end: String(data.query.end),
              format: "JSON",
            }).toString()}`,
          },
        ]}
      />
    </PageFrame>
  );
}

function Inner() {
  const params = useSearchParams();
  const parsed = parseSelection(params);
  const horizon = Math.min(30, Math.max(1, Number(params.get("horizon")) || 5));
  const defaultCountry = COUNTRIES.find((c) => c.name === "Palestine") || COUNTRIES[0];

  const sel: Selection = parsed || {
    lat: defaultCountry.lat,
    lon: defaultCountry.lng,
    name: defaultCountry.name,
    variable: DEFAULT_VARIABLE,
    start: defaultStart(),
    end: defaultEnd(),
  };

  return <Forecast sel={sel} horizon={horizon} />;
}

export default function ForecastView() {
  return (
    <Suspense fallback={<PageFrame title="Forecast"><Loading text="Loading..." /></PageFrame>}>
      <Inner />
    </Suspense>
  );
}
