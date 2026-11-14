"use client";

import React from "react";
import Link from "next/link";

/**
 * Scrollable page wrapper. The global stylesheet locks body scrolling for the
 * full-screen globe, so content pages scroll inside their own container.
 */
export default function PageFrame({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="h-screen overflow-y-auto bg-[#070a13] text-[#e2e8f0] select-text">
      <header className="sticky top-0 z-10 bg-[#070a13] border-b border-[#1f2937]">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-base sm:text-lg font-bold text-[#f8fafc] truncate">{title}</h1>
            {subtitle && <p className="text-xs text-[#9ca3af] truncate">{subtitle}</p>}
          </div>
          <Link href="/" className="shrink-0 text-xs px-3 py-1.5 rounded border border-[#374151] bg-[#111827] hover:bg-[#1f2937] text-[#cbd5e1]">
            Back to globe
          </Link>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-5 flex flex-col gap-5 pb-16">{children}</main>
    </div>
  );
}

export function Card({ title, children, className = "" }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`bg-[#111827] border border-[#1f2937] rounded-lg p-4 ${className}`}>
      {title && <h2 className="text-sm font-semibold text-[#f3f4f6] mb-3">{title}</h2>}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-lg p-3">
      <div className="text-[11px] uppercase tracking-wider text-[#9ca3af]">{label}</div>
      <div className="text-lg font-semibold text-[#f9fafb] mt-1">{value}</div>
      {hint && <div className="text-[11px] text-[#6b7280] mt-0.5">{hint}</div>}
    </div>
  );
}

export function Loading({ text }: { text: string }) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-lg p-8 text-center text-sm text-[#9ca3af]">
      <div className="inline-block w-5 h-5 border-2 border-[#374151] border-t-[#60a5fa] rounded-full animate-spin mb-3" />
      <p>{text}</p>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="bg-[#111827] border border-[#7f1d1d] rounded-lg p-6 text-sm">
      <p className="text-[#fca5a5]">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 px-3 py-1.5 text-xs rounded bg-[#1f2937] hover:bg-[#374151] text-[#e5e7eb]">
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
