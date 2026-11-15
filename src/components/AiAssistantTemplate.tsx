"use client";

import React from "react";
import Link from "next/link";
import type { Country } from "../data/countries";
import ChatBody from "./assistant/ChatBody";
import { useAssistantChat } from "./assistant/useAssistantChat";

interface AiAssistantTemplateProps {
  selectedCountry?: Country | null;
  onClose?: () => void;
}

export default function AiAssistantTemplate({
  selectedCountry,
  onClose,
}: AiAssistantTemplateProps) {
  const selected = React.useMemo(
    () => (selectedCountry ? { lat: selectedCountry.lat, lon: selectedCountry.lng, name: selectedCountry.name } : null),
    [selectedCountry],
  );
  const chat = useAssistantChat(selected);

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
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                  {selectedCountry.name}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">Real-time Earth Science Queries</p>
          </div>
        </div>

        {/* Header Action Controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={chat.reset}
            disabled={chat.pending || chat.items.length === 0}
            title="New conversation"
            aria-label="New conversation"
            className="px-2 py-1.5 rounded-lg bg-white/5 hover:bg-white/15 text-xs text-[#a1a1aa] hover:text-white border border-white/10 transition-colors disabled:opacity-40"
          >
            New
          </button>
          {/* Full Page Link */}
          <Link
            href={
              selected
                ? `/chat?lat=${selected.lat}&lon=${selected.lon}&name=${encodeURIComponent(selected.name)}`
                : "/chat"
            }
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

      <ChatBody chat={chat} variant="popup" placeholder="Ask a question in any language..." />
    </aside>
  );
}
