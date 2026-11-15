"use client";

import React, { Suspense, useMemo } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import ChatBody from "../../components/assistant/ChatBody";
import { useAssistantChat } from "../../components/assistant/useAssistantChat";

function ChatPageInner() {
  const params = useSearchParams();
  const selected = useMemo(() => {
    const latS = params.get("lat");
    const lonS = params.get("lon");
    if (!latS || !lonS) return null;
    const lat = Number(latS);
    const lon = Number(lonS);
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
    return { lat, lon, name: params.get("name") || `${lat.toFixed(2)}, ${lon.toFixed(2)}` };
  }, [params]);
  const chat = useAssistantChat(selected);

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#000000] text-[#f4f4f5] font-sans flex flex-col">
      {/* Top glassmorphic navigation bar */}
      <header className="h-16 px-6 border-b border-white/10 bg-[#18181b]/75 backdrop-blur-xl shadow-[0_4px_24px_0_rgba(0,0,0,0.5)] flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 group text-xs text-slate-300 hover:text-white transition-colors">
            <div className="w-8 h-8 rounded-lg overflow-hidden border border-amber-400/40 bg-black shadow-md flex items-center justify-center transition-transform group-hover:scale-105">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.jpg" alt="Logo" className="w-full h-full object-contain" />
            </div>
            <span className="font-bold text-white hidden sm:inline">Astro EARTH</span>
          </Link>
          <span className="text-white/20 hidden sm:inline">/</span>
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-slate-300 hover:text-white border border-white/10 text-xs font-semibold transition-all active:scale-95"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            <span>Back to 3D Globe</span>
          </Link>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
          <h1 className="text-xs font-bold text-white tracking-wide">AI Detective Assistant</h1>
        </div>

        <div className="flex items-center gap-2 text-xs">
          {selected && (
            <span className="text-xs font-mono px-2 py-1 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 max-w-[160px] truncate" title={`${selected.lat}, ${selected.lon}`}>
              {selected.name}
            </span>
          )}
          <button
            type="button"
            onClick={chat.reset}
            disabled={chat.pending || chat.items.length === 0}
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-slate-300 hover:text-white border border-white/10 text-xs font-semibold transition-all disabled:opacity-40"
          >
            New conversation
          </button>
        </div>
      </header>

      <ChatBody chat={chat} variant="page" placeholder="Ask in English or Arabic... (e.g. Has air temperature in Cairo risen since 1990?)" />
    </main>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageInner />
    </Suspense>
  );
}
