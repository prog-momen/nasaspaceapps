"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { COUNTRIES, Country } from "../data/countries";

let messageCounter = 0;
function generateMessageId(prefix: string): string {
  messageCounter += 1;
  return `${prefix}-${messageCounter}`;
}

function getFormattedTime(): string {
  const d = new Date();
  const h = String(d.getUTCHours()).padStart(2, "0");
  const m = String(d.getUTCMinutes()).padStart(2, "0");
  return `${h}:${m} UTC`;
}

function detectSuggestedVariable(query: string) {
  const q = query.toLowerCase();
  if (
    q.includes("rain") ||
    q.includes("precip") ||
    q.includes("storm") ||
    q.includes("flood") ||
    q.includes("مطر") ||
    q.includes("أمطار") ||
    q.includes("هطول")
  ) {
    return { key: "PRECTOTCORR", name: "Precipitation", reason: "Rain & snowfall observation" };
  }
  if (
    q.includes("max") ||
    q.includes("heat") ||
    q.includes("summer") ||
    q.includes("hot") ||
    q.includes("حر") ||
    q.includes("موجة حارة") ||
    q.includes("أعلى حرارة")
  ) {
    return { key: "T2M_MAX", name: "Maximum Air Temperature", reason: "Daytime extreme heat analysis" };
  }
  if (
    q.includes("min") ||
    q.includes("night") ||
    q.includes("cold") ||
    q.includes("frost") ||
    q.includes("صقيع") ||
    q.includes("برد") ||
    q.includes("أدنى حرارة")
  ) {
    return { key: "T2M_MIN", name: "Minimum Air Temperature", reason: "Nighttime cooling and frost recovery" };
  }
  if (q.includes("surface") || q.includes("skin") || q.includes("ground") || q.includes("سطح")) {
    return { key: "TS", name: "Surface Skin Temperature", reason: "Direct thermal satellite skin observation" };
  }
  if (
    q.includes("drought") ||
    q.includes("soil") ||
    q.includes("root") ||
    q.includes("crop") ||
    q.includes("farm") ||
    q.includes("جفاف") ||
    q.includes("تربة") ||
    q.includes("رطوبة")
  ) {
    return { key: "GWETROOT", name: "Root Zone Soil Wetness", reason: "Early indicator of agricultural drought" };
  }
  if (q.includes("evap") || q.includes("تبخر")) {
    return { key: "EVLAND", name: "Evaporation from Land", reason: "Hydrological water loss from soil and canopy" };
  }
  if (q.includes("humid") || q.includes("رطوبة نسبية")) {
    return { key: "RH2M", name: "Relative Humidity", reason: "Atmospheric moisture saturation level" };
  }
  if (
    q.includes("wind") ||
    q.includes("gust") ||
    q.includes("speed") ||
    q.includes("رياح") ||
    q.includes("عاصف")
  ) {
    return { key: "WS10M", name: "Wind Speed (10m)", reason: "Surface wind kinetics and storm dynamics" };
  }
  if (q.includes("cloud") || q.includes("overcast") || q.includes("غيم") || q.includes("سحاب")) {
    return { key: "CLOUD_AMT", name: "Cloud Amount", reason: "Sky coverage and solar shading fraction" };
  }
  if (
    q.includes("solar") ||
    q.includes("sun") ||
    q.includes("radiation") ||
    q.includes("energy") ||
    q.includes("شمس") ||
    q.includes("طاقة")
  ) {
    return { key: "ALLSKY_SFC_SW_DWN", name: "Solar Radiation at Surface", reason: "Incident solar energy reaching the ground" };
  }
  if (q.includes("pressure") || q.includes("barometer") || q.includes("ضغط")) {
    return { key: "PS", name: "Surface Pressure", reason: "Atmospheric air mass steering weather fronts" };
  }
  return { key: "T2M", name: "Air Temperature (2m)", reason: "Baseline thermal trend observation" };
}

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: string;
  dashboardLink?: {
    lat: number;
    lon: number;
    name: string;
    variable: string;
  };
  dataBrief?: {
    region?: string;
    coords?: string;
    variable?: string;
    slope?: string;
    pValue?: string;
    source?: string;
  };
}

interface AiAssistantTemplateProps {
  selectedCountry?: Country | null;
  onClose?: () => void;
}

export default function AiAssistantTemplate({
  selectedCountry,
  onClose,
}: AiAssistantTemplateProps) {
  // All data starts completely empty - zero mock or fake data
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing]);

  const handleSendMessage = useCallback(
    async (textToSend?: string) => {
      const query = (textToSend || inputPrompt).trim();
      if (!query) return;

      const userMsg: ChatMessage = {
        id: generateMessageId("user"),
        sender: "user",
        text: query,
        timestamp: getFormattedTime(),
      };

      setMessages((prev) => [...prev, userMsg]);
      if (!textToSend) setInputPrompt("");
      setIsProcessing(true);

      try {
        // Resolve target coordinates safely without 0,0 fallback
        const coordMatch = query.match(/(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)/);
        let resolvedLat = 31.95;
        let resolvedLon = 35.23;
        let resolvedName = selectedCountry?.name || "Palestine (Default Baseline)";

        if (coordMatch) {
          const pLat = parseFloat(coordMatch[1]);
          const pLon = parseFloat(coordMatch[2]);
          if (!isNaN(pLat) && !isNaN(pLon) && Math.abs(pLat) <= 90 && Math.abs(pLon) <= 180) {
            resolvedLat = pLat;
            resolvedLon = pLon;
            resolvedName = `Grid Cell (${Math.abs(pLat).toFixed(1)}°${pLat >= 0 ? "N" : "S"}, ${Math.abs(pLon).toFixed(1)}°${pLon >= 0 ? "E" : "W"})`;
          }
        } else {
          const matchedCountry = COUNTRIES.find(
            (c) =>
              query.toLowerCase().includes(c.name.toLowerCase()) ||
              query.toLowerCase().includes(c.code3.toLowerCase()) ||
              query.toLowerCase().includes(c.capital.toLowerCase())
          );
          if (matchedCountry) {
            resolvedLat = matchedCountry.lat;
            resolvedLon = matchedCountry.lng;
            resolvedName = matchedCountry.name;
          } else if (selectedCountry) {
            resolvedLat = selectedCountry.lat;
            resolvedLon = selectedCountry.lng;
            resolvedName = selectedCountry.name;
          }
        }

        // Smart Variable Recommender: pick optimal variable based on user question
        const suggestedVar = detectSuggestedVariable(query);

        // Query the real backend API with resolved coordinates & suggested variable
        const response = await fetch(
          `/api/ai/context?lat=${resolvedLat}&lon=${resolvedLon}&variable=${suggestedVar.key}&start=1990&end=2024&horizon=10`
        );

        if (response.ok) {
          const data = await response.json();
          const regionName = data.region?.name || resolvedName;
          const varName = data.variable?.name || suggestedVar.name;
          const varUnit = data.variable?.unit || "";
          const slopeVal = data.facts?.slope_per_year
            ? `${(data.facts.slope_per_year * 10).toFixed(3)} ${varUnit}/decade`
            : undefined;
          const pVal = data.facts?.p_value_mann_kendall;
          const verdict = data.facts?.verdict || "Observation completed";
          const totalChange = data.facts?.total_change
            ? `${data.facts.total_change > 0 ? "+" : ""}${data.facts.total_change.toFixed(2)} ${varUnit}`
            : undefined;

          let responseText = `🔍 **NASA Grounded Investigation: ${regionName}**\n\n`;
          responseText += `💡 **Suggested Variable:** ${varName} (${suggestedVar.reason})\n`;
          responseText += `📊 **Detective Verdict:** ${verdict}\n`;
          if (slopeVal) {
            responseText += `📈 **Rate of Change (Sen's Slope):** ${slopeVal}\n`;
          }
          if (totalChange) {
            responseText += `🌐 **Total Net Shift:** ${totalChange}\n`;
          }
          if (pVal !== undefined) {
            const isSig = typeof pVal === "number" ? pVal < 0.05 : String(pVal).includes("<");
            responseText += `🔬 **Statistical Significance:** ${pVal} (${isSig ? "Statistically Significant ✅" : "Not statistically significant yet ⏳"})\n`;
          }
          if (data.variable?.definition) {
            responseText += `\n*Definition: ${data.variable.definition}*`;
          }

          const aiMsg: ChatMessage = {
            id: generateMessageId("ai"),
            sender: "ai",
            text: responseText,
            timestamp: getFormattedTime(),
            dashboardLink: {
              lat: resolvedLat,
              lon: resolvedLon,
              name: regionName,
              variable: suggestedVar.key,
            },
            dataBrief: {
              region: regionName,
              coords: `${resolvedLat.toFixed(2)}° | ${resolvedLon.toFixed(2)}°`,
              variable: varName,
              slope: slopeVal,
              pValue: pVal !== undefined ? String(pVal) : undefined,
              source: data.source?.model,
            },
          };
          setMessages((prev) => [...prev, aiMsg]);
        } else {
          // Zero fake data: honest report of status
          const aiMsg: ChatMessage = {
            id: generateMessageId("ai"),
            sender: "ai",
            text: `No observational data returned from backend API for "${query}" (Status: ${response.status}). Zero simulated data is provided.`,
            timestamp: getFormattedTime(),
          };
          setMessages((prev) => [...prev, aiMsg]);
        }
      } catch {
        // Zero fake data: honest report of connection status
        const errorMsg: ChatMessage = {
          id: generateMessageId("ai-err"),
          sender: "ai",
          text: `Backend service is unreachable. Real-time satellite data could not be retrieved. Zero simulated data is returned.`,
          timestamp: getFormattedTime(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsProcessing(false);
      }
    },
    [inputPrompt, selectedCountry]
  );

  return (
    <aside className="w-full h-full flex flex-col bg-[#18181b]/80 backdrop-blur-xl border border-white/15 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.65)] overflow-hidden pointer-events-auto font-sans">
      {/* Realistic Glassmorphic Chat Header */}
      <header className="px-4 py-3 bg-[#0a0f1d]/90 border-b border-white/10 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg overflow-hidden border border-amber-400/50 bg-black shadow-[0_0_10px_rgba(245,158,11,0.3)] shrink-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.jpg" alt="AI Detective" className="w-full h-full object-contain" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-white flex items-center gap-1.5">
                <span>AI Detective</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              </h2>
              {selectedCountry && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                  {selectedCountry.name}
                </span>
              )}
            </div>
            <p className="text-[10px] text-slate-400">Real-time Earth Science Queries</p>
          </div>
        </div>

        {/* Header Action Controls */}
        <div className="flex items-center gap-1.5">
          {/* Full Page Link */}
          <Link
            href="/chat"
            aria-label="Expand to full page"
            title="Full Page View"
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/15 text-[#a1a1aa] hover:text-[#f4f4f5] border border-white/10 transition-colors"
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="15 3 21 3 21 9"></polyline>
              <polyline points="9 21 3 21 3 15"></polyline>
              <line x1="21" y1="3" x2="14" y2="10"></line>
              <line x1="3" y1="21" x2="10" y2="14"></line>
            </svg>
          </Link>

          {/* Close Popup Button */}
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close assistant popup"
              title="Close Popup"
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/15 text-[#a1a1aa] hover:text-white border border-white/10 transition-colors"
            >
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          )}
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-xs text-[#a1a1aa]">
            <div className="w-14 h-14 rounded-2xl overflow-hidden border border-amber-400/40 bg-black shadow-[0_0_20px_rgba(245,158,11,0.25)] flex items-center justify-center mb-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.jpg" alt="AI Ready" className="w-full h-full object-contain" />
            </div>
            <p className="font-bold text-white text-xs mb-1 flex items-center gap-1.5">
              <span>AI Detective Ready</span>
              <span className="text-amber-400">✦</span>
            </p>
            <p className="text-[11px] text-slate-400 leading-relaxed max-w-[240px]">
              No messages yet. Ask any question below to explore real NASA Earth observation metrics. Zero mock data.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === "user";
            return (
              <div
                key={msg.id}
                className={`flex flex-col gap-1 ${
                  isUser ? "items-end" : "items-start"
                }`}
              >
                <div className="flex items-center gap-1.5 text-[9px] text-[#71717a]">
                  {!isUser && (
                    <div className="w-3.5 h-3.5 rounded-full overflow-hidden bg-black border border-amber-400/40">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src="/logo.jpg" alt="AI" className="w-full h-full object-contain" />
                    </div>
                  )}
                  <span>{isUser ? "You" : "AI Detective"}</span>
                  <span>•</span>
                  <span>{msg.timestamp}</span>
                </div>

                <div
                  className={`max-w-[90%] p-3 rounded-xl text-xs leading-relaxed whitespace-pre-line shadow-sm ${
                    isUser
                      ? "bg-[#2563eb] text-white"
                      : "bg-[#27272a]/80 backdrop-blur-md text-[#f4f4f5] border border-white/10"
                  }`}
                >
                  {msg.text}
                </div>

                {/* Brief Card for Real Data */}
                {msg.dataBrief && msg.dataBrief.slope && (
                  <div className="w-full max-w-[90%] bg-[#09090b]/80 backdrop-blur-md border border-white/10 rounded-xl p-2.5 text-[10px] space-y-1">
                    <div className="flex justify-between text-[#a1a1aa]">
                      <span>Region:</span>
                      <span className="font-bold text-[#f4f4f5]">
                        {msg.dataBrief.region} ({msg.dataBrief.coords})
                      </span>
                    </div>
                    {msg.dataBrief.slope && (
                      <div className="flex justify-between text-[#a1a1aa]">
                        <span>Slope:</span>
                        <span className="font-mono font-bold text-[#60a5fa]">
                          {msg.dataBrief.slope}
                        </span>
                      </div>
                    )}
                    {msg.dataBrief.pValue && (
                      <div className="flex justify-between text-[#a1a1aa]">
                        <span>p-value:</span>
                        <span className="font-mono text-[#34d399]">
                          {msg.dataBrief.pValue}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Direct Action Link to Guided Dashboard */}
                {msg.dashboardLink && (
                  <Link
                    href={`/dashboard?lat=${msg.dashboardLink.lat}&lon=${msg.dashboardLink.lon}&name=${encodeURIComponent(
                      msg.dashboardLink.name
                    )}&variable=${msg.dashboardLink.variable}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl cosmic-gold-button text-[11px] font-bold shadow-md hover:scale-[1.02] active:scale-95 transition-all mt-1"
                  >
                    <span>📊 Open {msg.dashboardLink.variable} in Dashboard →</span>
                  </Link>
                )}
              </div>
            );
          })
        )}

        {isProcessing && (
          <div className="flex items-center gap-2 p-2.5 rounded-xl bg-white/5 border border-white/10 text-xs text-[#a1a1aa] w-fit">
            <span className="w-1.5 h-1.5 rounded-full bg-[#60a5fa] animate-ping"></span>
            <span className="text-[11px]">Connecting to backend API...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Glassmorphic Chat Input Form */}
      <footer className="p-3 bg-white/5 border-t border-white/10 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            placeholder="Type a message or country name..."
            className="flex-1 bg-[#09090b]/80 backdrop-blur-md border border-white/15 focus:border-[#2563eb] rounded-xl px-3.5 py-2.5 text-xs text-[#f4f4f5] placeholder-[#71717a] outline-none transition-colors"
          />

          <button
            type="submit"
            disabled={!inputPrompt.trim() || isProcessing}
            aria-label="Send Message"
            className="px-4 py-2.5 rounded-xl cosmic-gold-button disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold transition-all flex items-center justify-center shrink-0 shadow-md active:scale-95"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </form>
      </footer>
    </aside>
  );
}
