"use client";

import React from "react";
import type { Artifact, Citation } from "@/lib/assistant/types";
import { ArtifactView, visibleInline } from "./Artifacts";

// Safe renderer for the assistant's Markdown dialect. Builds React elements only (no raw HTML).

const CALLOUT: Record<string, { icon: string; cls: string }> = {
  key: { icon: "💡", cls: "border-amber-400/40 bg-amber-400/10" },
  warn: { icon: "⚠️", cls: "border-orange-400/40 bg-orange-400/10" },
  info: { icon: "ℹ️", cls: "border-sky-400/40 bg-sky-400/10" },
  good: { icon: "✅", cls: "border-emerald-400/40 bg-emerald-400/10" },
  hot: { icon: "🔥", cls: "border-red-400/40 bg-red-400/10" },
  cold: { icon: "❄️", cls: "border-cyan-400/40 bg-cyan-400/10" },
};

const isHttp = (u?: string) => !!u && /^https?:\/\//i.test(u);

function renderInline(s: string, cites: Citation[], keyBase: string): React.ReactNode[] {
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^)\s]+\)|\[\d{1,2}\]|\*[^*\s][^*]*\*)/g;
  const out: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(s))) {
    if (m.index > last) out.push(s.slice(last, m.index));
    const tok = m[1];
    const key = `${keyBase}-${k++}`;
    if (tok.startsWith("**")) out.push(<strong key={key}>{renderInline(tok.slice(2, -2), cites, key)}</strong>);
    else if (tok.startsWith("`")) out.push(<code key={key} className="px-1 rounded bg-white/10 font-mono text-[0.95em]">{tok.slice(1, -1)}</code>);
    else if (/^\[\d{1,2}\]$/.test(tok)) {
      const c = cites.find((x) => x.index === Number(tok.slice(1, -1)));
      if (c && isHttp(c.url)) {
        out.push(
          <a key={key} href={c.url} target="_blank" rel="noopener noreferrer" title={c.title} className="text-[#60a5fa] hover:underline align-super text-[0.75em]">
            {tok}
          </a>,
        );
      } else {
        out.push(
          <sup key={key} title={c?.title} className="text-[#60a5fa]">
            {tok}
          </sup>,
        );
      }
    } else if (tok.startsWith("[")) {
      const mm = /^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/.exec(tok);
      out.push(
        mm ? (
          <a key={key} href={mm[2]} target="_blank" rel="noopener noreferrer" className="text-[#60a5fa] underline">
            {mm[1]}
          </a>
        ) : (
          tok
        ),
      );
    } else out.push(<em key={key}>{renderInline(tok.slice(1, -1), cites, key)}</em>);
    last = re.lastIndex;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}

export function Markdown({
  text,
  citations = [],
  inline = [],
  compact = false,
}: {
  text: string;
  citations?: Citation[];
  inline?: Artifact[];
  compact?: boolean;
}) {
  const nodes: React.ReactNode[] = [];
  // The model sometimes glues a heading onto the end of a sentence ("...definition.## Title").
  const lines = String(text || "")
    .replace(/\r/g, "")
    .replace(/([.!?:؟])(#{1,3}\s)/g, "$1\n\n$2")
    .split("\n");
  let list: React.ReactNode[] | null = null;
  let listOrdered = false;
  let quote: { kind: string; parts: React.ReactNode[] } | null = null;
  let usedInline = false;
  let n = 0;
  const key = () => `b${n++}`;

  const flushList = () => {
    if (list) {
      const items = list;
      nodes.push(
        listOrdered ? (
          <ol key={key()} className="list-decimal ps-5 space-y-0.5">{items}</ol>
        ) : (
          <ul key={key()} className="list-disc ps-5 space-y-0.5">{items}</ul>
        ),
      );
      list = null;
    }
  };
  const flushQuote = () => {
    if (quote) {
      const c = CALLOUT[quote.kind];
      nodes.push(
        c ? (
          <div key={key()} dir="auto" role="note" className={`flex gap-2 rounded-lg border px-2.5 py-2 ${c.cls}`}>
            <span aria-hidden>{c.icon}</span>
            <div>{quote.parts}</div>
          </div>
        ) : (
          <blockquote key={key()} dir="auto" className="border-s-2 border-white/30 ps-2 text-[#d4d4d8]">{quote.parts}</blockquote>
        ),
      );
      quote = null;
    }
  };
  const flush = () => {
    flushList();
    flushQuote();
  };

  for (const raw of lines) {
    const tr = raw.trim();
    let m: RegExpExecArray | null;
    if (!tr) {
      flush();
      continue;
    }
    if (/^\[\[(inline|chart|table)\]\]$/.test(tr)) {
      flush();
      if (!usedInline && inline.length) {
        usedInline = true;
        nodes.push(
          <div key={key()}>
            {visibleInline(inline).map((a, i) => (
              <ArtifactView key={i} artifact={a} />
            ))}
          </div>,
        );
      }
      continue;
    }
    if ((m = /^(#{1,3})\s+(.*)$/.exec(tr))) {
      flush();
      nodes.push(
        <h3 key={key()} dir="auto" className="font-bold text-[1.05em] text-white">
          {renderInline(m[2], citations, `h${n}`)}
        </h3>,
      );
      continue;
    }
    if ((m = /^\^\s*(.*)$/.exec(tr))) {
      flush();
      nodes.push(
        <p key={key()} dir="auto" className="text-[0.85em] text-[#a1a1aa]">
          {renderInline(m[1], citations, `n${n}`)}
        </p>,
      );
      continue;
    }
    if (tr.startsWith("ℹ️")) {
      flush();
      nodes.push(
        <p key={key()} dir="auto" className="text-[0.85em] text-sky-300/90">
          {renderInline(tr, citations, `i${n}`)}
        </p>,
      );
      continue;
    }
    if (tr.startsWith(">")) {
      flushList();
      const body = tr.replace(/^>\s?/, "");
      const c = /^\[!(key|warn|info|good|hot|cold)\]\s*(.*)$/i.exec(body);
      if (c) {
        flushQuote();
        quote = { kind: c[1].toLowerCase(), parts: renderInline(c[2], citations, `q${n}`) };
      } else if (quote) {
        quote.parts = [...quote.parts, <br key={`br${n}`} />, ...renderInline(body, citations, `q${n}`)];
      } else {
        quote = { kind: "", parts: renderInline(body, citations, `q${n}`) };
      }
      continue;
    }
    flushQuote();
    const li = /^\s*(?:[-*•])\s+(.*)$/.exec(raw) ?? /^\s*\d+[.)]\s+(.*)$/.exec(raw);
    if (li) {
      const ordered = /^\s*\d/.test(raw);
      if (list && listOrdered !== ordered) flushList();
      if (!list) {
        list = [];
        listOrdered = ordered;
      }
      list.push(
        <li key={`li${n++}`} dir="auto">
          {renderInline(li[1], citations, `l${n}`)}
        </li>,
      );
      continue;
    }
    flushList();
    nodes.push(
      <p key={key()} dir="auto">
        {renderInline(tr, citations, `p${n}`)}
      </p>,
    );
  }
  flush();
  // Inline artifacts the text did not place go at the end.
  if (!usedInline && inline.length) {
    nodes.push(
      <div key={key()}>
        {visibleInline(inline).map((a, i) => (
          <ArtifactView key={i} artifact={a} />
        ))}
      </div>,
    );
  }
  return <div className={`space-y-1.5 ${compact ? "" : "leading-relaxed"}`}>{nodes}</div>;
}
