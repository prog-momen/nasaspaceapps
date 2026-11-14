"use client";

import React from "react";
import Link from "next/link";

/**
 * Scrollable or full-viewport page wrapper.
 */
export default function PageFrame({
  title,
  subtitle,
  children,
  noScroll = false,
  maxWidth = "max-w-6xl",
  theme = "dark",
  hideHeader = false,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  noScroll?: boolean;
  maxWidth?: string;
  theme?: "dark" | "clay";
  hideHeader?: boolean;
}) {
  const isClay = theme === "clay";

  return (
    <div
      className={`h-screen ${
        noScroll ? "overflow-hidden flex flex-col" : "overflow-y-auto"
      } ${
        isClay ? "bg-[#080d16] text-[#f1f5f9]" : "bg-[#070a13] text-[#e2e8f0]"
      } select-text font-sans`}
    >
      {!hideHeader && (
        <header
          className={`sticky top-0 z-20 ${
            isClay
              ? "bg-[#0a111c]/95 backdrop-blur-md border-b border-white/10 shadow-lg"
              : "bg-[#070a13]/95 backdrop-blur-md border-b border-[#1f2937]"
          } shrink-0`}
        >
          <div className={`${maxWidth} mx-auto px-4 py-2 flex items-center justify-between gap-3`}>
            <div className="flex items-center gap-3 min-w-0">
              <Link href="/" className="flex items-center gap-2.5 shrink-0 group">
                <div className="relative w-8 h-8 rounded-lg overflow-hidden border border-amber-400/40 bg-black shadow-md flex items-center justify-center transition-transform group-hover:scale-105">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src="/logo.jpg" alt="EarthTrend Logo" className="w-full h-full object-contain" />
                </div>
              </Link>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                      isClay
                        ? "text-amber-400 bg-amber-950/40 border border-amber-500/30"
                        : "text-amber-400 bg-amber-950/30 border border-amber-500/20"
                    }`}
                  >
                    NASA EarthTrend Detective
                  </span>
                </div>
                <h1
                  className={`text-sm sm:text-base font-bold truncate mt-0.5 ${
                    isClay ? "text-white" : "text-[#f8fafc]"
                  }`}
                >
                  {title}
                </h1>
                {subtitle && (
                  <p className={`text-[11px] truncate ${isClay ? "text-slate-400" : "text-[#9ca3af]"}`}>
                    {subtitle}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Link
                href="/"
                className={`text-xs px-3 py-1.5 rounded-xl border transition-all flex items-center gap-1.5 active:scale-95 shadow-sm font-semibold ${
                  isClay
                    ? "dark-clay-button text-slate-200 hover:text-white"
                    : "border-white/10 bg-[#18181b]/80 hover:bg-[#27272a] text-[#cbd5e1] hover:text-white"
                }`}
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
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="2" y1="12" x2="22" y2="12"></line>
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                </svg>
                <span>Back to Globe</span>
              </Link>
            </div>
          </div>
        </header>
      )}

      {noScroll ? (
        <main
          className={`flex-1 min-h-0 w-full ${maxWidth} mx-auto px-2 sm:px-3 py-2 flex flex-col overflow-hidden`}
        >
          {children}
        </main>
      ) : (
        <main className={`max-w-5xl mx-auto px-4 py-6 flex flex-col gap-6 pb-20`}>{children}</main>
      )}
    </div>
  );
}

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`bg-[#111827] border border-[#1f2937] rounded-xl p-3.5 sm:p-4 shadow-lg ${className}`}>
      {title && <h2 className="text-xs sm:text-sm font-bold text-[#f3f4f6] mb-2">{title}</h2>}
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-3 shadow-md">
      <div className="text-[10px] uppercase tracking-wider text-[#9ca3af] font-medium">{label}</div>
      <div className="text-base font-bold text-[#f9fafb] mt-0.5">{value}</div>
      {hint && <div className="text-[10px] text-[#6b7280] mt-0.5">{hint}</div>}
    </div>
  );
}

export function Loading({ text }: { text: string }) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-8 text-center text-sm text-[#9ca3af] shadow-lg">
      <div className="inline-block w-6 h-6 border-2 border-[#374151] border-t-[#60a5fa] rounded-full animate-spin mb-3" />
      <p>{text}</p>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="bg-[#111827] border border-[#7f1d1d] rounded-xl p-6 text-sm shadow-lg">
      <p className="text-[#fca5a5]">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 px-3 py-1.5 text-xs rounded-lg bg-[#1f2937] hover:bg-[#374151] text-[#e5e7eb] font-medium transition-all"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export const VERDICT = {
  significant: { label: "Statistically significant", cls: "bg-[#14532d] text-[#86efac] border-[#166534]" },
  weak_evidence: { label: "Weak evidence", cls: "bg-[#78350f] text-[#fcd34d] border-[#92400e]" },
  not_significant: { label: "Not significant", cls: "bg-[#1f2937] text-[#d1d5db] border-[#374151]" },
} as const;

export const fmt = (v: number, d = 2) =>
  Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(d);
export const fmtP = (p: number) => (p < 0.001 ? "< 0.001" : p.toFixed(3));
export const signed = (v: number, d = 2) => `${v >= 0 ? "+" : "-"}${fmt(Math.abs(v), d)}`;
