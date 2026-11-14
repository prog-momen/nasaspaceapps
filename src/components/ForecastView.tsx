"use client";

import React, { Suspense } from "react";
import { useAsync } from "../lib/useAsync";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import PageFrame, { Card, ErrorBox, Loading, Stat, VERDICT, fmt, signed } from "./PageFrame";
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
