"use client";

import React from "react";

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  sunAngle: number;
  onSetSunAngle: (angle: number) => void;
  showClouds: boolean;
  onToggleClouds: (val: boolean) => void;
  showBorders: boolean;
  onToggleBorders: (val: boolean) => void;
  showGraticule: boolean;
  onToggleGraticule: (val: boolean) => void;
  autoSpin: boolean;
  onToggleAutoSpin: (val: boolean) => void;
  lang: "ar" | "en";
}

export default function SettingsPanel({
  isOpen,
  onClose,
  sunAngle,
  onSetSunAngle,
  showClouds,
  onToggleClouds,
  showBorders,
  onToggleBorders,
  showGraticule,
  onToggleGraticule,
  autoSpin,
  onToggleAutoSpin,
  lang,
}: SettingsPanelProps) {
  const isAr = lang === "ar";
  if (!isOpen) return null;

  return (
    <aside
      dir={isAr ? "rtl" : "ltr"}
      className="fixed top-16 right-3 w-72 max-w-[calc(100vw-1.5rem)] bg-[#0d1424] border border-[#1e293b] rounded-2xl p-4 shadow-2xl z-40 flex flex-col gap-3 text-xs text-[#cbd5e1]"
    >
      <div className="flex items-center justify-between border-b border-[#1f2937] pb-2">
        <h3 className="font-bold text-white text-xs">
          {isAr ? "إعدادات الكرة الأرضية والطبقات" : "Globe & Layer Settings"}
        </h3>
        <button
          onClick={onClose}
          className="text-[#9ca3af] hover:text-white w-6 h-6 rounded flex items-center justify-center hover:bg-[#1f2937] transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      {/* Sun Angle Slider */}
      <div>
        <div className="flex items-center justify-between text-[11px] mb-1">
          <span className="font-semibold text-[#f8fafc]">{isAr ? "زاوية إضاءة الشمس:" : "Sun Lighting Angle:"}</span>
          <span className="font-mono text-[#fcd34d]">{sunAngle}° UTC</span>
        </div>
        <input
          type="range"
          min="0"
          max="360"
          value={sunAngle}
          onChange={(e) => onSetSunAngle(parseInt(e.target.value))}
          className="w-full accent-[#38bdf8] h-1.5 cursor-pointer"
        />
      </div>

      {/* Toggles */}
      <div className="space-y-1.5">
        <label className="flex items-center justify-between cursor-pointer bg-[#070a13] p-2 rounded-lg border border-[#1f2937]">
          <span className="font-medium text-white">{isAr ? "طبقة السحب" : "Cloud Layer"}</span>
          <input
            type="checkbox"
            checked={showClouds}
            onChange={(e) => onToggleClouds(e.target.checked)}
            className="w-4 h-4 accent-[#2563eb]"
          />
        </label>

        <label className="flex items-center justify-between cursor-pointer bg-[#070a13] p-2 rounded-lg border border-[#1f2937]">
          <span className="font-medium text-white">{isAr ? "حدود الدول السياسية" : "Political Borders"}</span>
          <input
            type="checkbox"
            checked={showBorders}
            onChange={(e) => onToggleBorders(e.target.checked)}
            className="w-4 h-4 accent-[#2563eb]"
          />
        </label>

        <label className="flex items-center justify-between cursor-pointer bg-[#070a13] p-2 rounded-lg border border-[#1f2937]">
          <span className="font-medium text-white">{isAr ? "خطوط الطول والعرض" : "Graticule Grid"}</span>
          <input
            type="checkbox"
            checked={showGraticule}
            onChange={(e) => onToggleGraticule(e.target.checked)}
            className="w-4 h-4 accent-[#2563eb]"
          />
        </label>

        <label className="flex items-center justify-between cursor-pointer bg-[#070a13] p-2 rounded-lg border border-[#1f2937]">
          <span className="font-medium text-white">{isAr ? "الدوران التلقائي للأرض" : "Auto-Rotation"}</span>
          <input
            type="checkbox"
            checked={autoSpin}
            onChange={(e) => onToggleAutoSpin(e.target.checked)}
            className="w-4 h-4 accent-[#2563eb]"
          />
        </label>
      </div>
    </aside>
  );
}

