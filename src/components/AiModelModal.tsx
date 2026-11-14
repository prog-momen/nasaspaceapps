"use client";

import React, { useState } from "react";

interface AiModelModalProps {
  isOpen: boolean;
  onClose: () => void;
  lang: "ar" | "en";
}

export default function AiModelModal({
  isOpen,
  onClose,
  lang,
}: AiModelModalProps) {
  const isAr = lang === "ar";
  const [modelType, setModelType] = useState("xgboost");
  const [apiKey, setApiKey] = useState("");
  const [saved, setSaved] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 800);
  };

  return (
    <div
      dir={isAr ? "rtl" : "ltr"}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
    >
      <div className="bg-[#0b1324] border border-[#f59e0b] rounded-2xl max-w-lg w-full p-5 shadow-2xl flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-[#1f2937] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#38220c] border border-[#f59e0b] flex items-center justify-center text-[#fcd34d] font-bold text-xs">
              AI
            </div>
            <div>
              <h3 className="text-base font-extrabold text-white">
                {isAr ? "ربط موديل الذكاء الاصطناعي (Custom AI Model)" : "Custom AI Model Integration"}
              </h3>
              <p className="text-[11px] text-[#9ca3af]">
                {isAr ? "إعدادات وتوصيل خوارزمية التنبؤ بحرائق الغابات" : "Configure team wildfire prediction weights and endpoints"}
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

        {/* Model Architecture & Features */}
        <div className="space-y-3 text-xs">
          <div className="p-3 bg-[#070a13] rounded-xl border border-[#1f2937] space-y-1.5">
            <span className="font-bold text-[#fcd34d] block">
              {isAr ? "مدخلات النموذج (Input Features from NASA Satellites):" : "NASA Satellite Feature Inputs:"}
            </span>
            <ul className="list-disc list-inside space-y-1 text-[#cbd5e1] text-[11px]">
              <li><strong className="text-white">MODIS LST:</strong> {isAr ? "شذوذ حرارة سطح الأرض الساعية والشهرية" : "Land Surface Temperature anomaly"}</li>
              <li><strong className="text-white">GPM / GLDAS:</strong> {isAr ? "عجز الرطوبة النسبية ورطوبة طبقة الجذور" : "Root-zone soil wetness & rainfall deficit"}</li>
              <li><strong className="text-white">MERRA-2:</strong> {isAr ? "متجهات وسرعة الرياح السطحية (10 أمتار)" : "Surface wind speeds & gust frequency"}</li>
              <li><strong className="text-white">MODIS NDVI:</strong> {isAr ? "كثافة وجفاف الوقود النباتي الغابي" : "Canopy moisture stress & vegetation fuel load"}</li>
            </ul>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#94a3b8] mb-1">
              {isAr ? "نوع النموذج الخوارزمي:" : "Model Engine Architecture:"}
            </label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value)}
              className="w-full bg-[#111827] border border-[#374151] rounded-lg p-2 text-white text-xs outline-none"
            >
              <option value="xgboost">Gradient Boosting / XGBoost (F1: 0.84, Default)</option>
              <option value="randomforest">Random Forest Classifier (Ensemble)</option>
              <option value="custom_api">Custom Team REST API Webhook</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[#94a3b8] mb-1">
              {isAr ? "مفتاح API أو رابط الخادم المحلي:" : "API Key or Endpoint URL (Optional):"}
            </label>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="http://localhost:8000/predict or Bearer token"
              className="w-full bg-[#111827] border border-[#374151] rounded-lg p-2 text-white text-xs outline-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-[#1f2937]">
          <span className="text-[10px] text-[#34d399]">
            {saved ? (isAr ? "تم حفظ الإعدادات بنجاح!" : "Configuration saved!") : ""}
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg bg-[#1f2937] hover:bg-[#374151] text-white text-xs font-semibold"
            >
              {isAr ? "إلغاء" : "Cancel"}
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg bg-[#d97706] hover:bg-[#b45309] text-white text-xs font-bold"
            >
              {isAr ? "حفظ التوصيل" : "Save & Connect"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

