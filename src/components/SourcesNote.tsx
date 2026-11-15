"use client";

import React from "react";

export interface SourcesNoteProps {
  /** Data sources and methods the result depends on (what the feature is built on). */
  relies: string[];
  /** Concrete inputs this particular result actually used (place, period, records, citations). */
  used: string[];
  /** Clickable references: the exact data request and the method papers. */
  links?: { label: string; url: string }[];
  /** Labels; the chat passes Arabic labels when the answer is in Arabic. */
  labels?: { relies: string; used: string; title: string };
  dir?: "ltr" | "rtl" | "auto";
  className?: string;
}

const DEFAULT_LABELS = { relies: "Relies on", used: "Used in this result", title: "Sources" };

/** Compact source line shown under every analysis or assistant answer. Plain text only, no links to keep it short. */
export default function SourcesNote({ relies, used, links = [], labels = DEFAULT_LABELS, dir = "auto", className = "" }: SourcesNoteProps) {
  if (!relies.length && !used.length && !links.length) return null;
  return (
    <div dir={dir} className={`mt-2 rounded-lg border border-white/10 bg-black/30 px-2.5 py-2 text-[11px] leading-relaxed text-[#a1a1aa] ${className}`}>
      <div className="mb-0.5 font-semibold text-[#d4d4d8]">{labels.title}</div>
      {relies.length > 0 && (
        <div>
          <span className="text-[#e4e4e7]">{labels.relies}:</span> {relies.join(" · ")}
        </div>
      )}
      {used.length > 0 && (
        <div>
          <span className="text-[#e4e4e7]">{labels.used}:</span> {used.join(" · ")}
        </div>
      )}
      {links.length > 0 && (
        <ul className="mt-1 space-y-0.5 break-all">
          {links.map((l) => (
            <li key={l.url}>
              <a href={l.url} target="_blank" rel="noopener noreferrer" className="text-[#93c5fd] hover:underline">
                {l.label}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
