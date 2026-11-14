"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { COUNTRIES } from "../../data/countries";

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

export default function ChatPage() {
  // Empty data initial state - zero fake or mock data
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
        const matchedCountry = COUNTRIES.find(
          (c) =>
            query.toLowerCase().includes(c.name.toLowerCase()) ||
            query.toLowerCase().includes(c.code3.toLowerCase()) ||
            query.toLowerCase().includes(c.capital.toLowerCase())
        );

        const lat = matchedCountry ? matchedCountry.lat : 0;
        const lon = matchedCountry ? matchedCountry.lng : 0;

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

          let responseText = `Investigation Report for ${regionName}:\n`;
          if (data.variable?.name) {
            responseText += `• Variable: ${data.variable.name}\n`;
          }
          if (slopeVal) {
            responseText += `• Measured rate of change: ${slopeVal}\n`;
          }
          if (pVal !== undefined) {
            responseText += `• Mann-Kendall p-value: ${pVal}\n`;
          }
          if (data.source?.model) {
            responseText += `• Source Model: ${data.source.model}`;
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
          text: `Backend service is unreachable. Real-time satellite records could not be fetched. Zero simulated data is returned.`,
          timestamp: getFormattedTime(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsProcessing(false);
      }
    },
    [inputPrompt]
  );

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#000000] text-[#f4f4f5] font-sans flex flex-col">
      {/* Top Realistic Glassmorphic Navigation Bar */}
      <header className="h-16 px-6 border-b border-white/10 bg-[#18181b]/75 backdrop-blur-xl shadow-[0_4px_24px_0_rgba(0,0,0,0.5)] flex items-center justify-between z-20 shrink-0">
        {/* Link back to Homepage */}
        <Link
          href="/"
          className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/15 text-[#f4f4f5] border border-white/10 text-xs font-bold transition-all shadow-sm active:scale-95"
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
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          <span>Back to 3D Earth</span>
        </Link>

        {/* Title */}
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#10b981]"></span>
          <h1 className="text-xs font-bold text-[#f4f4f5] tracking-wide">
            EarthScope AI Assistant (Full Page)
          </h1>
        </div>

        {/* Telemetry Indicator */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-[10px] font-mono px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-[#34d399] font-bold">
            API READY
          </span>
        </div>
      </header>

      {/* Main Chat Content Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl w-full mx-auto flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-xs text-[#a1a1aa]">
            <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 text-[#a1a1aa] flex items-center justify-center mb-4 shadow-inner">
              <svg
                width="24"
                height="24"
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
            <p className="font-bold text-[#f4f4f5] text-sm mb-1.5">
              Full Page AI Assistant
            </p>
            <p className="text-[11px] text-[#71717a] max-w-sm leading-relaxed">
              All data is empty. Enter any country, region, or question below to query real Earth observation data. Zero fake data mode enabled.
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
                  className={`max-w-2xl p-4 rounded-xl text-xs leading-relaxed whitespace-pre-line shadow-sm ${
                    isUser
                      ? "bg-[#2563eb] text-white"
                      : "bg-[#18181b]/80 backdrop-blur-xl text-[#f4f4f5] border border-white/10"
                  }`}
                >
                  {msg.text}
                </div>

                {msg.dataBrief && msg.dataBrief.slope && (
                  <div className="w-full max-w-2xl bg-[#09090b]/80 backdrop-blur-md border border-white/10 rounded-xl p-3 text-[11px] space-y-1 mt-1">
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
                    {msg.dataBrief.source && (
                      <div className="flex justify-between text-[#a1a1aa]">
                        <span>Source:</span>
                        <span className="text-[#a1a1aa]">
                          {msg.dataBrief.source}
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
          <div className="flex items-center gap-2 p-3 rounded-xl bg-white/5 border border-white/10 text-xs text-[#a1a1aa] w-fit">
            <span className="w-2 h-2 rounded-full bg-[#60a5fa] animate-ping"></span>
            <span>Querying backend Earth science API...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Realistic Glassmorphic Bottom Chat Input Form */}
      <footer className="p-4 border-t border-white/10 bg-[#18181b]/75 backdrop-blur-xl shrink-0 z-20 shadow-[0_-4px_24px_0_rgba(0,0,0,0.5)]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="max-w-3xl mx-auto flex items-center gap-2"
        >
          <input
            type="text"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            placeholder="Type your question or country name..."
            className="flex-1 bg-[#09090b]/80 backdrop-blur-md border border-white/15 focus:border-[#2563eb] rounded-xl px-4 py-2.5 text-xs text-[#f4f4f5] placeholder-[#71717a] outline-none transition-colors"
          />

          <button
            type="submit"
            disabled={!inputPrompt.trim() || isProcessing}
            aria-label="Send Query"
            className="px-5 py-2.5 rounded-xl bg-[#2563eb] hover:bg-[#1d4ed8] disabled:bg-white/5 disabled:text-[#71717a] text-white text-xs font-bold transition-all flex items-center gap-2 shrink-0 shadow-md active:scale-95"
          >
            <span>Send</span>
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
    </main>
  );
}
