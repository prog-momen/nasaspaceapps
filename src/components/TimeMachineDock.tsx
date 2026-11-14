"use client";

import React, { useEffect, useState } from "react";
import { EnvLayerKey } from "../data/nasaTrends";

interface TimeMachineDockProps {
  currentYear: number;
  onSetYear: (yr: number) => void;
  envLayer: EnvLayerKey;
  onSetEnvLayer: (layer: EnvLayerKey) => void;
  activeTargetName: string;
  activeCoords: string;
  lang: "ar" | "en";
}

export default function TimeMachineDock({
  currentYear,
  onSetYear,
  envLayer,
  onSetEnvLayer,
  activeTargetName,
  activeCoords,
  lang,
}: TimeMachineDockProps) {
  const isAr = lang === "ar";
  const [isPlaying, setIsPlaying] = useState(false);

  // Play/pause time series animation loop
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      onSetYear(currentYear >= 2050 ? 1985 : currentYear + 1);
    }, 450);
    return () => clearInterval(interval);
  }, [isPlaying, currentYear, onSetYear]);

  const layers: { key: EnvLayerKey; labelAr: string; labelEn: string; sat: string }[] = [
    { key: "natural", labelAr: "الوضع العادي (طبيعي)", labelEn: "Natural Earth", sat: "TrueColor" },
    { key: "temp", labelAr: "حرارة السطح (MODIS)", labelEn: "Surface Temp", sat: "MODIS" },
    { key: "water", labelAr: "الأمطار والتربة (GPM)", labelEn: "Moisture & Rain", sat: "GPM/GLDAS" },
    { key: "winds", labelAr: "الرياح (MERRA-2)", labelEn: "Winds", sat: "MERRA-2" },
    { key: "veg", labelAr: "الغطاء النباتي (NDVI)", labelEn: "Vegetation", sat: "MODIS NDVI" },
    { key: "fires", labelAr: "الحرائق النشطة (FIRMS)", labelEn: "Active Fires", sat: "FIRMS" },
  ];

  return (
    <footer
      dir={isAr ? "rtl" : "ltr"}
      className="fixed bottom-2.5 inset-x-3 z-30 flex flex-col gap-1.5 pointer-events-none"
    >
      {/* Time Machine Timeline Bar */}
      <div className="bg-[#0b1324] border border-[#1e293b] px-3.5 py-2 rounded-2xl flex flex-wrap items-center justify-between gap-2.5 pointer-events-auto shadow-2xl text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying((p) => !p)}
            className="w-7 h-7 rounded-lg bg-[#1e293b] hover:bg-[#334155] text-[#38bdf8] flex items-center justify-center transition-colors"
            title={isPlaying ? "Pause Timeline" : "Play Timeline"}
          >
            {isPlaying ? (
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16"></rect>
                <rect x="14" y="4" width="4" height="16"></rect>
              </svg>
            ) : (
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
            )}
          </button>

          <div className="flex items-center gap-1.5 font-bold">
            <span className="text-[#9ca3af] hidden sm:inline">{isAr ? "الزمن:" : "Time:"}</span>
            <span className="px-2 py-0.5 rounded bg-[#1e3a8a] text-white font-mono font-extrabold text-xs">
              {currentYear}
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#064e3b] text-[#6ee7b7] hidden md:inline-block">
              {currentYear <= 2026
                ? (isAr ? "أرصاد ناسا الفضائية (1985-2026)" : "NASA Satellite Observations (1985-2026)")
                : (isAr ? "توقعات الذكاء الاصطناعي وCMIP6 (2026-2050)" : "AI Projections & CMIP6 (2026-2050)")}
            </span>
          </div>
        </div>

        {/* Range Slider */}
        <div className="flex-1 min-w-[150px] max-w-md flex items-center gap-2 text-[10px] font-mono">
          <span className="text-[#38bdf8] font-bold">1985</span>
          <input
            type="range"
            min="1985"
            max="2050"
            value={currentYear}
            onChange={(e) => onSetYear(parseInt(e.target.value))}
            className="w-full accent-[#38bdf8] h-1.5 cursor-pointer"
          />
          <span className="text-[#f43f5e] font-bold">2050</span>
        </div>

        {/* Preset Year Buttons */}
        <div className="flex items-center gap-1 text-[10px] font-mono font-bold">
          <button
            onClick={() => onSetYear(1990)}
            className="px-2 py-1 rounded bg-[#111827] border border-[#1f2937] hover:bg-[#1f2937] text-[#cbd5e1]"
          >
            1990
          </button>
          <button
            onClick={() => onSetYear(2010)}
            className="px-2 py-1 rounded bg-[#111827] border border-[#1f2937] hover:bg-[#1f2937] text-[#cbd5e1] hidden sm:inline-block"
          >
            2010
          </button>
          <button
            onClick={() => onSetYear(2026)}
            className="px-2 py-1 rounded bg-[#1e3a8a] border border-[#3b82f6] text-white"
          >
            2026 ({isAr ? "الآن" : "Now"})
          </button>
          <button
            onClick={() => onSetYear(Math.min(2050, currentYear + 5))}
            className="px-2 py-1 rounded bg-[#38220c] border border-[#f59e0b] text-[#fcd34d]"
          >
            +5y AI
          </button>
          <button
            onClick={() => onSetYear(2050)}
            className="px-2 py-1 rounded bg-[#33111b] border border-[#f43f5e] text-[#fecdd3]"
          >
            2050
          </button>
        </div>
      </div>

      {/* Layer Switcher & HUD Row */}
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <div className="bg-[#0b1324] border border-[#1e293b] p-1 rounded-2xl flex items-center gap-1 pointer-events-auto overflow-x-auto max-w-full text-xs shadow-xl">
          <span className="text-[10px] font-bold text-[#94a3b8] px-2 hidden lg:inline whitespace-nowrap">
            {isAr ? "الرؤية الفضائية:" : "NASA Layer:"}
          </span>

          {layers.map((l) => {
            const isActive = envLayer === l.key;
            return (
              <button
                key={l.key}
                onClick={() => onSetEnvLayer(l.key)}
                className={`px-2.5 py-1 rounded-xl text-[11px] font-bold whitespace-nowrap border transition-colors ${
                  isActive
                    ? "bg-[#1e3a8a] border-[#3b82f6] text-white"
                    : "bg-[#111827] border-[#1f2937] text-[#9ca3af] hover:text-white hover:bg-[#1f2937]"
                }`}
              >
                {isAr ? l.labelAr : l.labelEn}
              </button>
            );
          })}
        </div>

        {/* Real-time Target HUD */}
        <div className="bg-[#0b1324] border border-[#1e293b] px-3 py-1.5 rounded-2xl flex items-center gap-2.5 text-xs pointer-events-auto shadow-xl ml-auto sm:ml-0">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#10b981]"></span>
            <span className="font-mono text-[#38bdf8] font-bold text-[11px]">
              {activeCoords}
            </span>
          </div>
          <div className="h-3 w-px bg-[#374151]"></div>
          <span className="font-bold text-white text-[11px] truncate max-w-[140px]">
            {activeTargetName}
          </span>
        </div>
      </div>
    </footer>
  );
}
