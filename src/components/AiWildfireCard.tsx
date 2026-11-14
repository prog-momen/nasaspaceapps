"use client";

import React, { useState } from "react";
import { PilotRegion, PILOT_CLUSTERS } from "../data/nasaTrends";

interface AiWildfireCardProps {
  currentClusterKey: string;
  onSelectCluster: (key: string) => void;
  selectedRegion: PilotRegion;
  onSelectRegion: (r: PilotRegion) => void;
  lang: "ar" | "en";
}

export default function AiWildfireCard({
  currentClusterKey,
  onSelectCluster,
  selectedRegion,
  onSelectRegion,
  lang,
}: AiWildfireCardProps) {
  const isAr = lang === "ar";
  const cluster = PILOT_CLUSTERS[currentClusterKey] || PILOT_CLUSTERS.palestine_jordan;

  // Interactive weather simulation sliders
  const [tempOffset, setTempOffset] = useState<number>(0);
  const [dryOffset, setDryOffset] = useState<number>(0);

  // Recalculate dynamic risk based on sliders
  const dynamicTemp = (selectedRegion.temp + tempOffset).toFixed(1);
  const dynamicDry = Math.round(selectedRegion.dry + dryOffset);
  const calculatedRisk = Math.min(
    99,
    Math.max(10, Math.round(selectedRegion.risk + tempOffset * 8 - dryOffset * 0.4))
  );

  const riskBadgeColor =
    calculatedRisk >= 80 ? "text-[#ef4444]" : calculatedRisk >= 60 ? "text-[#f59e0b]" : "text-[#10b981]";

  const resetSliders = () => {
    setTempOffset(0);
    setDryOffset(0);
  };

  return (
    <aside
      dir={isAr ? "rtl" : "ltr"}
      className="w-full sm:w-[380px] max-w-[calc(100vw-1.5rem)] bg-[#0d1424] border border-[#f59e0b] rounded-2xl p-3.5 shadow-2xl flex flex-col gap-2.5 max-h-[calc(100vh-10rem)] overflow-y-auto"
    >
      {/* Cluster Header & Country Selector */}
      <div className="flex items-center justify-between gap-2 border-b border-[#1f2937] pb-2">
        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#38220c] border border-[#f59e0b] text-[#fcd34d]">
          {isAr ? "نموذج الذكاء الاصطناعي (FIRMS AI)" : "AI Model (FIRMS AI)"}
        </span>

        <select
          value={currentClusterKey}
          onChange={(e) => onSelectCluster(e.target.value)}
          className="bg-[#111827] text-white text-[11px] font-bold px-2 py-1 rounded border border-[#374151] outline-none cursor-pointer"
        >
          <option value="palestine_jordan">
            {isAr ? "فلسطين والأردن" : "Palestine & Jordan"}
          </option>
          <option value="spain">{isAr ? "إسبانيا (الغابات)" : "Spain (Woodlands)"}</option>
        </select>
      </div>

      {/* Selected Region Title & Pills */}
      <div>
        <h2 className="text-sm font-extrabold text-white">
          {isAr ? selectedRegion.nameAr : selectedRegion.nameEn}
        </h2>
        <p className="text-[10px] text-[#9ca3af] mt-0.5">
          {isAr
            ? "انقر على الدبابيس الملونة فوق الأرض أو الأزرار أدناه للتبديل:"
            : "Click globe pins or buttons below to explore regional micro-zones:"}
        </p>

        <div className="flex flex-wrap gap-1 mt-1.5">
          {cluster.regions.map((r) => {
            const isSelected = r.id === selectedRegion.id;
            return (
              <button
                key={r.id}
                onClick={() => {
                  onSelectRegion(r);
                  resetSliders();
                }}
                className={`px-2 py-1 rounded text-[10px] font-bold border transition-colors ${
                  isSelected
                    ? "bg-[#2563eb] border-[#3b82f6] text-white"
                    : "bg-[#111827] border-[#1f2937] text-[#9ca3af] hover:text-white"
                }`}
              >
                {isAr ? r.nameAr.replace(/^\d+\.\s*/, "") : r.nameEn.replace(/^\d+\.\s*/, "")}
              </button>
            );
          })}
        </div>
      </div>

      {/* Step 1: Observed NASA Data */}
      <div className="p-2.5 rounded-xl bg-[#091b29] border border-[#0284c7] text-xs flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-[11px] font-bold text-[#38bdf8]">
          <span>{isAr ? "1. المرصود من أقمار ناسا (Observed)" : "1. Observed from NASA Satellites"}</span>
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#0369a1] text-[#e0f2fe]">
            MODIS + FIRMS
          </span>
        </div>

        <div className="grid grid-cols-3 gap-1.5 text-center">
          <div className="bg-[#070a13] p-1.5 rounded border border-[#1e293b]">
            <span className="text-[9px] text-[#94a3b8] block">{isAr ? "حرارة السطح" : "Surface Temp"}</span>
            <span className="text-xs font-extrabold text-[#fcd34d] font-mono">+{dynamicTemp}°C</span>
          </div>

          <div className="bg-[#070a13] p-1.5 rounded border border-[#1e293b]">
            <span className="text-[9px] text-[#94a3b8] block">{isAr ? "عجز الرطوبة" : "Moisture Deficit"}</span>
            <span className="text-xs font-extrabold text-[#38bdf8] font-mono">{dynamicDry}%</span>
          </div>

          <div className="bg-[#070a13] p-1.5 rounded border border-[#1e293b]">
            <span className="text-[9px] text-[#94a3b8] block">{isAr ? "بؤر سابقة" : "Past Fires"}</span>
            <span className="text-xs font-extrabold text-[#f43f5e] font-mono">{selectedRegion.fires}</span>
          </div>
        </div>
      </div>

      {/* Step 2: AI Model Risk Estimate */}
      <div className="p-2.5 rounded-xl bg-[#29180c] border border-[#f59e0b] text-xs flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-[#fbbf24] block">
              {isAr ? "2. تقدير الذكاء الاصطناعي (Model Estimate)" : "2. AI Model Risk Prediction"}
            </span>
            <div className={`text-sm font-extrabold ${riskBadgeColor}`}>
              {calculatedRisk >= 80
                ? isAr ? "خطر حرائق مرتفع" : "High Wildfire Risk"
                : calculatedRisk >= 60
                ? isAr ? "خطر متوسط" : "Moderate Risk"
                : isAr ? "خطر منخفض" : "Low Risk"} ({calculatedRisk}%)
            </div>
          </div>

          <div className="w-10 h-10 rounded-xl bg-[#111827] border border-[#f59e0b] flex flex-col items-center justify-center">
            <span className="text-xs font-bold text-[#fcd34d] font-mono">{calculatedRisk}%</span>
            <span className="text-[7px] text-[#9ca3af]">AI RISK</span>
          </div>
        </div>

        <p className="text-[10px] text-[#fde68a] leading-relaxed">
          {isAr ? selectedRegion.expAr : selectedRegion.expEn}
        </p>

        {/* Slide 12 Model Metrics */}
        <div className="bg-[#111827] border border-[#374151] rounded-lg p-1.5 text-center">
          <div className="flex items-center justify-between text-[9px] font-bold text-[#cbd5e1] mb-1">
            <span>{isAr ? "اختبار النموذج (Testing Benchmarks):" : "Model Testing Benchmarks:"}</span>
            <span className="font-mono text-[#38bdf8]">F1 = 0.84</span>
          </div>
          <div className="grid grid-cols-3 gap-1">
            <div className="bg-[#070a13] p-1 rounded border border-[#064e3b]">
              <span className="text-[8px] text-[#94a3b8] block">{isAr ? "تم كشفها" : "Recall"}</span>
              <span className="text-[10px] font-bold text-[#34d399] font-mono">{selectedRegion.caught}%</span>
            </div>
            <div className="bg-[#070a13] p-1 rounded border border-[#881337]">
              <span className="text-[8px] text-[#94a3b8] block">{isAr ? "فائتة" : "Missed"}</span>
              <span className="text-[10px] font-bold text-[#f43f5e] font-mono">{selectedRegion.missed}%</span>
            </div>
            <div className="bg-[#070a13] p-1 rounded border border-[#78350f]">
              <span className="text-[8px] text-[#94a3b8] block">{isAr ? "إنذار خاطئ" : "False"}</span>
              <span className="text-[10px] font-bold text-[#fbbf24] font-mono">{selectedRegion.falseAlarm}%</span>
            </div>
          </div>
        </div>

        {/* Dynamic Simulation Sliders */}
        <div className="pt-1.5 border-t border-[#451a03]">
          <div className="flex items-center justify-between text-[10px] font-bold text-[#fcd34d] mb-1">
            <span>{isAr ? "تعديل الطقس لاختبار الذكاء الاصطناعي:" : "Weather Stress Test Sliders:"}</span>
            <button onClick={resetSliders} className="text-[#9ca3af] hover:text-white underline text-[9px]">
              {isAr ? "إعادة ضبط" : "Reset"}
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div>
              <div className="flex justify-between text-[#cbd5e1] mb-0.5">
                <span>{isAr ? "الحرارة:" : "Temp:"}</span>
                <span className="font-mono text-[#fcd34d]">+{dynamicTemp}°C</span>
              </div>
              <input
                type="range"
                min="-2"
                max="3"
                step="0.2"
                value={tempOffset}
                onChange={(e) => setTempOffset(parseFloat(e.target.value))}
                className="w-full accent-[#f59e0b] h-1 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-[#cbd5e1] mb-0.5">
                <span>{isAr ? "الجفاف:" : "Dryness:"}</span>
                <span className="font-mono text-[#38bdf8]">{dynamicDry}%</span>
              </div>
              <input
                type="range"
                min="-30"
                max="20"
                step="2"
                value={dryOffset}
                onChange={(e) => setDryOffset(parseFloat(e.target.value))}
                className="w-full accent-[#38bdf8] h-1 cursor-pointer"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Step 3: Trusted Actions */}
      <div className="p-2.5 rounded-xl bg-[#092318] border border-[#10b981] text-xs flex flex-col gap-1.5">
        <span className="text-[11px] font-bold text-[#34d399]">
          {isAr ? "3. إجراءات استجابة موثوقة (Civil Protection Guidance)" : "3. Trusted Response Actions"}
        </span>

        {(isAr ? selectedRegion.actionsAr : selectedRegion.actionsEn).map((act, i) => (
          <div key={i} className="bg-[#070a13] p-1.5 rounded border border-[#064e3b] text-[10px]">
            <div className="font-bold text-[#f8fafc]">{act.title}</div>
            <div className="flex items-center justify-between text-[#9ca3af] mt-0.5 text-[9px]">
              <span>{act.src}</span>
              <span className="text-[#38bdf8]">{act.reason}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="text-[9px] text-[#6b7280] pt-1 border-t border-[#1f2937]">
        {isAr
          ? "التقدير الإحصائي والذكاء الاصطناعي أداة مساندة للإنذار المبكر وليست جزما قطعيا بحتمية الحريق."
          : "AI risk assessment provides decision support and early warning; always follow official civil defense directives."}
      </div>
    </aside>
  );
}

