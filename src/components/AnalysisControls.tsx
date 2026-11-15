"use client";

import React, { useEffect, useState } from "react";
import {
  DEFAULT_VARIABLE,
  MIN_YEAR,
  currentYear,
  defaultEnd,
  defaultStart,
  fetchVariables,
  type Selection,
  type VariableDef,
} from "../lib/api-client";

interface Props {
  lat: number;
  lon: number;
  name: string;
  initial?: Partial<Pick<Selection, "variable" | "start" | "end">>;
  submitLabel: string;
  onApply: (s: Selection) => void;
}

const CATEGORY_LABEL: Record<string, string> = {
  atmosphere: "Atmosphere",
  land: "Land",
  water: "Water",
  energy: "Energy",
};

/** Environmental variable + time period picker, backed by /api/variables. */
export default function AnalysisControls({ lat, lon, name, initial, submitLabel, onApply }: Props) {
  const [variables, setVariables] = useState<VariableDef[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [variable, setVariable] = useState(initial?.variable ?? DEFAULT_VARIABLE);
  const [start, setStart] = useState(initial?.start ?? defaultStart());
  const [end, setEnd] = useState(initial?.end ?? defaultEnd());

  useEffect(() => {
    fetchVariables()
      .then((r) => setVariables(r.variables))
      .catch(() => setLoadError(true));
  }, []);

  const selected = variables.find((v) => v.key === variable);
  const periodError =
    start < MIN_YEAR
      ? `Data starts in ${MIN_YEAR}.`
      : end > currentYear()
        ? `The latest year is ${currentYear()}.`
        : end - start < 4
          ? "Choose at least 5 years."
          : null;
  const groups = Object.entries(CATEGORY_LABEL).map(([cat, label]) => ({
    label,
    items: variables.filter((v) => v.category === cat),
  }));

  const fieldClass =
    "w-full bg-[#0b0f19] border border-[#1f2937] rounded px-2 py-1.5 text-xs text-[#f3f4f6] focus:outline-none focus:border-[#2563eb]";

  return (
    <div className="flex flex-col gap-3 text-xs">
      <label className="flex flex-col gap-1">
        <span className="text-[#9ca3af] text-[11px] uppercase tracking-wider">Environmental variable</span>
        <select value={variable} onChange={(e) => setVariable(e.target.value)} className={fieldClass} disabled={!variables.length}>
          {!variables.length && <option value={variable}>{loadError ? "Could not load variables" : "Loading..."}</option>}
          {groups.map(
            (g) =>
              g.items.length > 0 && (
                <optgroup key={g.label} label={g.label}>
                  {g.items.map((v) => (
                    <option key={v.key} value={v.key}>
                      {v.name} ({v.unit})
                    </option>
                  ))}
                </optgroup>
              ),
          )}
        </select>
      </label>

      {selected && (
        <p className="text-[#9ca3af] leading-relaxed bg-[#0b0f19] border border-[#1f2937] rounded p-2">
          {selected.definition} <span className="text-[#6b7280]">Higher means: {selected.higher_means}</span>
        </p>
      )}

      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[#9ca3af] text-[11px] uppercase tracking-wider">From year</span>
          <input type="number" min={MIN_YEAR} max={currentYear()} value={start} onChange={(e) => setStart(Number(e.target.value))} className={fieldClass} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[#9ca3af] text-[11px] uppercase tracking-wider">To year</span>
          <input type="number" min={MIN_YEAR} max={currentYear()} value={end} onChange={(e) => setEnd(Number(e.target.value))} className={fieldClass} />
        </label>
      </div>
      {periodError && <p className="text-[#f59e0b]">{periodError}</p>}

      <button
        disabled={!!periodError}
        onClick={() => onApply({ lat, lon, name, variable, start, end })}
        className="py-2 px-3 bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold rounded transition-colors"
      >
        {submitLabel}
      </button>
    </div>
  );
}
