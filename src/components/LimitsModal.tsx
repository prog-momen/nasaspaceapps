"use client";

import React from "react";

interface LimitsModalProps {
  isOpen: boolean;
  onClose: () => void;
  lang: "ar" | "en";
}

export default function LimitsModal({
  isOpen,
  onClose,
  lang,
}: LimitsModalProps) {
  const isAr = lang === "ar";
  if (!isOpen) return null;

  return (
    <div
      dir={isAr ? "rtl" : "ltr"}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
    >
      <div className="bg-[#0b1324] border border-[#2563eb] rounded-2xl max-w-xl w-full p-5 shadow-2xl flex flex-col gap-4 max-h-[90vh] overflow-y-auto text-xs text-[#cbd5e1]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#1f2937] pb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#1e3a8a] border border-[#3b82f6] flex items-center justify-center text-[#93c5fd] font-bold text-xs">
              i
            </div>
            <div>
              <h3 className="text-base font-extrabold text-white">
                {isAr ? "حدود النمذجة والمصادر العلمية" : "Model Limitations & Scientific Sources"}
              </h3>
              <p className="text-[11px] text-[#9ca3af]">
                {isAr ? "منهجية تحليل السلاسل الزمنية وأرصاد وكالة ناسا" : "NASA Earth Science Data & Time-Series Methodology"}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg bg-[#111827] hover:bg-[#1f2937] text-[#9ca3af] hover:text-white flex items-center justify-center transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="space-y-3 leading-relaxed">
          <div className="p-3 bg-[#070a13] rounded-xl border border-[#1f2937]">
            <h4 className="font-bold text-[#60a5fa] mb-1">
              {isAr ? "1. مستشعرات وأقمار ناسا المستخدمة:" : "1. NASA Missions & Satellite Instruments:"}
            </h4>
            <ul className="list-disc list-inside space-y-1 text-[11px]">
              <li><strong>MODIS (Terra & Aqua):</strong> {isAr ? "حرارة سطح الأرض ومؤشر الغطاء النباتي NDVI" : "Land surface temperature & NDVI vegetation index"}</li>
              <li><strong>GPM (Global Precipitation Measurement):</strong> {isAr ? "بيانات الهطول المطري والبخار الجوي" : "Precipitation and atmospheric moisture rates"}</li>
              <li><strong>MERRA-2 & GLDAS:</strong> {isAr ? "نماذج المحاكاة المناخية ورطوبة طبقة الجذور وسرعة الرياح" : "Root-zone soil moisture and 10m wind fields"}</li>
              <li><strong>FIRMS (Active Fire System):</strong> {isAr ? "رصد البؤر الحرارية وحرائق الغابات النشطة" : "Active thermal anomalies and fire detection"}</li>
            </ul>
          </div>

          <div className="p-3 bg-[#070a13] rounded-xl border border-[#1f2937]">
            <h4 className="font-bold text-[#fcd34d] mb-1">
              {isAr ? "2. الدلالة الإحصائية وإزالة الدورة الموسمية:" : "2. Statistical Significance & Seasonal Cycle:"}
            </h4>
            <p className="text-[11px]">
              {isAr
                ? "كما نصت وثيقة التحدي (challenge.txt)، تتسم المتغيرات البيئية بدورات موسمية قوية تخفي أحياناً الاتجاهات طويلة الأمد. نقوم بطرح المتوسط الشهري لتنقية البيانات، وتطبيق اختبار مان-كيندال اللابارامتري (Mann-Kendall test) لحساب قيمة p ومعامل Sen's Slope لضمان أن الاتجاه ليس وليد الصدفة."
                : "As noted in the NASA challenge guidelines, Earth science variables exhibit strong seasonal cycles that mask long-term trends. Our engine performs seasonal cycle subtraction before running non-parametric Mann-Kendall and Sen's slope tests to confirm significance without assuming normality."}
            </p>
          </div>

          <div className="p-3 bg-[#070a13] rounded-xl border border-[#1f2937]">
            <h4 className="font-bold text-[#ef4444] mb-1">
              {isAr ? "3. حدود التنبؤ والتعقيد اللاخطي:" : "3. Non-Linearity & Prediction Boundaries:"}
            </h4>
            <p className="text-[11px]">
              {isAr
                ? "الاتجاهات المناخية ليست خطية دائماً؛ التوقعات لعام 2050 تعتمد على سيناريوهات CMIP6 الرسمية (SSP1-2.6 / SSP2-4.5 / SSP5-8.5). تنبؤات حرائق الذكاء الاصطناعي هي مؤشرات مساندة لاتخاذ القرار والإنذار المبكر وليست بديلاً عن قرارات الحماية المدنية الميدانية."
                : "Climate systems are inherently non-linear; 2050 projections reflect standard CMIP6 shared socioeconomic pathways (SSPs). AI wildfire estimates provide decision support and early warning indicators rather than deterministic guarantees."}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-2 border-t border-[#1f2937]">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-bold transition-colors"
          >
            {isAr ? "حسناً، فهمت" : "Understood"}
          </button>
        </div>
      </div>
    </div>
  );
}

