"use client";

import React, { useState } from "react";
import { CountryTrend } from "../data/nasaTrends";

interface CountriesDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  countries: CountryTrend[];
  selectedCountry: CountryTrend | null;
  onSelectCountry: (c: CountryTrend) => void;
  lang: "ar" | "en";
}

export default function CountriesDrawer({
  isOpen,
  onClose,
  countries,
  selectedCountry,
  onSelectCountry,
  lang,
}: CountriesDrawerProps) {
  const isAr = lang === "ar";
  const [search, setSearch] = useState("");

  if (!isOpen) return null;

  const filtered = countries.filter((c) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return (
      c.nameAr.toLowerCase().includes(q) ||
      c.nameEn.toLowerCase().includes(q) ||
      c.code2.toLowerCase().includes(q) ||
      c.code3.toLowerCase().includes(q)
    );
  });

  return (
    <aside
      dir={isAr ? "rtl" : "ltr"}
      className="fixed top-16 right-3 bottom-28 w-80 max-w-[calc(100vw-1.5rem)] bg-[#0d1424] border border-[#1e293b] rounded-2xl shadow-2xl z-40 flex flex-col overflow-hidden text-xs text-[#cbd5e1]"
    >
      {/* Header */}
      <div className="p-3 border-b border-[#1f2937] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-white text-xs">
            {isAr ? "انتقال سريع للدول والمناطق" : "World Countries & Regions"}
          </h3>
          <button
            onClick={onClose}
            className="w-6 h-6 rounded flex items-center justify-center text-[#9ca3af] hover:text-white hover:bg-[#1f2937]"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={isAr ? "ابحث عن دولة (فلسطين، الأردن، إسبانيا)..." : "Search countries..."}
          className="w-full bg-[#111827] border border-[#374151] focus:border-[#38bdf8] rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-[#6b7280] outline-none"
        />
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filtered.map((c) => {
          const isSelected = selectedCountry?.key === c.key;
          return (
            <button
              key={c.key}
              onClick={() => {
                onSelectCountry(c);
                onClose();
              }}
              className={`w-full p-2 rounded-lg border text-right flex items-center justify-between transition-colors ${
                isSelected
                  ? "bg-[#1e3a8a] border-[#3b82f6] text-white"
                  : "bg-[#111827] border-[#1f2937] text-[#cbd5e1] hover:bg-[#1f2937]"
              }`}
            >
              <div className="flex flex-col text-right">
                <span className="font-bold text-white text-xs">
                  {isAr ? c.nameAr : c.nameEn}
                </span>
                <span className="text-[10px] text-[#9ca3af]">
                  {c.lat.toFixed(1)}°N, {c.lon.toFixed(1)}°E
                </span>
              </div>

              <div className="flex flex-col items-end gap-1">
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#374151] text-[#93c5fd]">
                  {c.tempAnomaly}
                </span>
                <span className="text-[9px] text-[#34d399] font-medium">
                  {c.stats.isSignificant ? (isAr ? "دال إحصائياً" : "Significant") : ""}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div className="p-2 border-t border-[#1f2937] bg-[#070a13] text-[10px] text-[#94a3b8] text-center">
        {isAr
          ? "انقر على أي دولة فوق الكرة الأرضية 3D لعرض تحليلات ناسا"
          : "Click any country on the 3D globe to load NASA POWER time series"}
      </div>
    </aside>
  );
}

