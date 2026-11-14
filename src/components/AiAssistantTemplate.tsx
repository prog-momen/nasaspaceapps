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

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: string;
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
        // Resolve target coordinates from selected country or query
        const matchedCountry =
          COUNTRIES.find(
            (c) =>
              query.toLowerCase().includes(c.name.toLowerCase()) ||
              query.toLowerCase().includes(c.code3.toLowerCase()) ||
              query.toLowerCase().includes(c.capital.toLowerCase())
          ) || selectedCountry;

        const lat = matchedCountry ? matchedCountry.lat : 0;
        const lon = matchedCountry ? matchedCountry.lng : 0;

        // Query the real backend API
        const response = await fetch(
          `/api/ai/context?lat=${lat}&lon=${lon}&variable=T2M&start=1990&end=2024&horizon=10`
        );

        if (response.ok) {
          const data = await response.json();
          const regionName = data.region?.name || matchedCountry?.name || "Target Coordinates";
          const slopeVal = data.facts?.slope_per_year
            ? `${(data.facts.slope_per_year * 10).toFixed(2)} / decade`
            : undefined;
          const pVal = data.facts?.p_value_mann_kendall;

          let responseText = `Analysis for ${regionName}:\n`;
          if (data.variable?.name) {
            responseText += `• Variable: ${data.variable.name}\n`;
          }
          if (slopeVal) {
            responseText += `• Rate of change: ${slopeVal}\n`;
          }
          if (pVal !== undefined) {
            responseText += `• Mann-Kendall p-value: ${pVal}\n`;
          }
          if (data.source?.model) {
            responseText += `• Source: ${data.source.model}`;
          }

          const aiMsg: ChatMessage = {
            id: generateMessageId("ai"),
            sender: "ai",
            text: responseText,
            timestamp: getFormattedTime(),
            dataBrief: {
              region: regionName,
              coords: `${lat.toFixed(2)} | ${lon.toFixed(2)}`,
              variable: data.variable?.name,
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
            text: `No observational data returned from backend API for "${query}" (Status: ${response.status}). No simulated or mock data is provided.`,
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
      <header className="px-4 py-3 bg-white/5 border-b border-white/10 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#10b981]"></span>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold text-[#f4f4f5]">AI Assistant</h2>
              {selectedCountry && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 text-[#a1a1aa] border border-white/10">
                  {selectedCountry.name}
                </span>
              )}
            </div>
            <p className="text-[10px] text-[#a1a1aa]">Real-time Earth Science Queries</p>
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
            <div className="w-11 h-11 rounded-2xl bg-white/5 border border-white/10 text-[#a1a1aa] flex items-center justify-center mb-3 shadow-inner">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
            </div>
            <p className="font-semibold text-[#f4f4f5] text-xs mb-1">
              AI Assistant Ready
            </p>
            <p className="text-[11px] text-[#71717a] leading-relaxed max-w-[220px]">
              No messages yet. Send a query below to fetch authentic NASA observation data.
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
                  <span>{isUser ? "User" : "AI Assistant"}</span>
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
            className="px-4 py-2.5 rounded-xl bg-[#2563eb] hover:bg-[#1d4ed8] disabled:bg-white/5 disabled:text-[#71717a] text-white text-xs font-bold transition-all flex items-center justify-center shrink-0 shadow-md active:scale-95"
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
