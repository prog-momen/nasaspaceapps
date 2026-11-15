"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { dashboardHref, forecastHref } from "@/lib/assistant/links";
import type { AssistantResponse, ChatItem, Panel } from "@/lib/assistant/types";
import { ArtifactView } from "./Artifacts";
import { Markdown } from "./Markdown";
import type { useAssistantChat } from "./useAssistantChat";

type Chat = ReturnType<typeof useAssistantChat>;

const OUTCOME: Record<string, { en: string; ar: string; tone: string }> = {
  answered: { en: "Answered", ar: "تمت الإجابة", tone: "good" },
  zero_detections: { en: "Valid query, zero detections", ar: "طلب صالح، صفر كشوف", tone: "" },
  no_data: { en: "No matching data", ar: "لا توجد بيانات مطابقة", tone: "warn" },
  unsupported: { en: "Unsupported", ar: "غير مدعوم", tone: "warn" },
  needs_credentials: { en: "Needs a key", ar: "يحتاج مفتاحًا", tone: "warn" },
  provider_outage: { en: "Provider unavailable", ar: "المزود غير متاح", tone: "warn" },
  model_quota: { en: "Model unavailable", ar: "النموذج غير متاح", tone: "warn" },
  ambiguous: { en: "Needs clarification", ar: "يحتاج توضيحًا", tone: "warn" },
  insufficient_evidence: { en: "Insufficient evidence", ar: "أدلة غير كافية", tone: "warn" },
  pending: { en: "Task running", ar: "المهمة قيد التنفيذ", tone: "warn" },
  error: { en: "Error", ar: "خطأ", tone: "bad" },
};
const TONE_CLS: Record<string, string> = {
  good: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  warn: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  bad: "bg-red-500/15 text-red-300 border-red-500/30",
  hot: "bg-red-500/15 text-red-300 border-red-500/30",
  cold: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  "": "bg-white/5 text-[#a1a1aa] border-white/10",
};

function Chip({ children, tone = "", title }: { children: React.ReactNode; tone?: string; title?: string }) {
  return (
    <span title={title} className={`inline-block px-2 py-0.5 rounded-full border text-[10px] ${TONE_CLS[tone] ?? TONE_CLS[""]}`}>
      {children}
    </span>
  );
}

export function PanelView({ panel, response }: { panel: Panel; response: AssistantResponse }) {
  const src = panel.source;
  const metrics = panel.metrics ?? [];
  return (
    <div className="space-y-2.5 text-xs">
      <div>
        <h3 dir="auto" className="font-bold text-sm text-white">
          {panel.title}
        </h3>
        {panel.subtitle && (
          <div dir="auto" className="text-[11px] text-[#a1a1aa]">
            {panel.subtitle}
          </div>
        )}
      </div>
      {metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-1.5">
          {metrics.map((m, i) => (
            <div key={i} title={m.basis} className={`rounded-lg border px-2 py-1.5 ${TONE_CLS[m.tone && m.tone !== "neutral" ? m.tone : ""] ?? TONE_CLS[""]}`}>
              <div className="text-[10px] opacity-80">{m.label}</div>
              <div className="font-semibold text-[12px]">
                {m.value === null || m.value === undefined ? "-" : String(m.value)}
                {m.unit ? <span className="text-[10px] opacity-70"> {m.unit}</span> : null}
              </div>
            </div>
          ))}
        </div>
      )}
      {(panel.artifacts ?? []).map((a, i) => (
        <ArtifactView key={i} artifact={a} />
      ))}
      {src && (
        <div className="text-[10px] text-[#a1a1aa] space-y-0.5">
          <div className="font-semibold text-[#d4d4d8]">Source</div>
          <div>
            {[src.provider, src.product].filter(Boolean).join(" · ")}
            {src.live === true ? " · live" : src.cache ? ` · cache: ${src.cache}` : ""}
            {src.retrieved_at ? ` · ${src.retrieved_at.slice(0, 16).replace("T", " ")}Z` : ""}
          </div>
          {(src.links ?? []).map((l, i) =>
            /^https?:\/\//i.test(l.url) ? (
              <a key={i} href={l.url} target="_blank" rel="noopener noreferrer" className="text-[#60a5fa] hover:underline me-2">
                {l.label}
              </a>
            ) : null,
          )}
          {src.attribution && <div>{src.attribution}</div>}
        </div>
      )}
      {(panel.limitations ?? []).length > 0 && (
        <details className="text-[10px] text-[#a1a1aa]">
          <summary className="cursor-pointer text-[#d4d4d8]">Limits &amp; caveats</summary>
          <ul className="list-disc ps-4 mt-1 space-y-0.5">
            {panel.limitations!.map((l, i) => (
              <li key={i} dir="auto">
                {l}
              </li>
            ))}
          </ul>
        </details>
      )}
      {response.tools && response.tools.length > 0 && (
        <div className="text-[10px] text-[#71717a]">Tools: {response.tools.map((t) => t.name).join(", ")}</div>
      )}
    </div>
  );
}

function Bubble({
  item,
  chat,
  variant,
  active,
  onSelect,
}: {
  item: ChatItem;
  chat: Chat;
  variant: "popup" | "page";
  active: boolean;
  onSelect: (id: string) => void;
}) {
  const isUser = item.role === "user";
  const r = item.response;
  const popup = variant === "popup";
  const dash = r ? dashboardHref(r) : item.dashboardLink ? `/dashboard?lat=${item.dashboardLink.lat}&lon=${item.dashboardLink.lon}&name=${encodeURIComponent(item.dashboardLink.name)}&variable=${item.dashboardLink.variable}` : null;
  const fc = r ? forecastHref(r) : null;
  const lang = r?.language;
  const oc = r?.outcome ? (OUTCOME[r.outcome] ?? { en: r.outcome, ar: r.outcome, tone: "" }) : null;
  const hasPanel = !!r?.panel && r.panel.status === "ok";

  return (
    <div className={`flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
      <div className="flex items-center gap-1.5 text-[9px] text-[#71717a]">
        {!isUser && (
          <div className="w-3.5 h-3.5 rounded-full overflow-hidden bg-black border border-amber-400/40">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.jpg" alt="AI" className="w-full h-full object-contain" />
          </div>
        )}
        <span>{isUser ? "You" : "AI Detective"}</span>
        <span>•</span>
        <span>{item.time}</span>
      </div>

      {isUser ? (
        <div dir="auto" className="max-w-[90%] p-3 rounded-xl text-xs leading-relaxed whitespace-pre-line shadow-sm bg-[#2563eb] text-white">
          {item.text}
        </div>
      ) : (
        <div
          onClick={() => hasPanel && !popup && onSelect(item.id)}
          className={`${popup ? "max-w-[96%]" : "max-w-full"} w-fit p-3 rounded-xl text-xs shadow-sm bg-[#27272a]/80 backdrop-blur-md text-[#f4f4f5] border ${
            active && !popup && hasPanel ? "border-amber-400/50" : item.error ? "border-red-500/40" : "border-white/10"
          } ${hasPanel && !popup ? "cursor-pointer" : ""}`}
        >
          {item.offline && (
            <div className="mb-1.5">
              <Chip tone="warn">Offline grounded mode (AI service unavailable)</Chip>
            </div>
          )}
          {item.error && <div className="mb-1 text-[10px] font-semibold text-red-300">Error</div>}
          {r ? (
            <Markdown text={r.answer} citations={r.citations} inline={r.inline} compact={popup} />
          ) : (
            <Markdown text={item.offline ? item.text.split("\n\n").slice(1).join("\n\n") : item.text} />
          )}

          {r && (
            <div className="flex flex-wrap gap-1 mt-2">
              {oc && <Chip tone={oc.tone}>{lang === "ar" ? oc.ar : oc.en}</Chip>}
              {r.answer_source && r.answer_source !== "none" && (
                <Chip title="answer source">{r.answer_source === "claude" && r.model ? `claude · ${r.model}` : r.answer_source}</Chip>
              )}
              {r.model_notice?.text && <Chip tone="warn">{r.model_notice.text}</Chip>}
            </div>
          )}

          {r?.conflict && (
            <div className="mt-2 rounded-lg border border-amber-400/30 bg-amber-400/10 p-2 space-y-1.5">
              <div className="text-[11px] text-amber-200">The message and the selected location differ. Which should I use?</div>
              {r.conflict.items.map((c, i) => (
                <div key={i} dir="auto" className="text-[10px] text-[#d4d4d8]">
                  {c.field}: «{String(c.message_value)}» vs «{String(c.controls_value)}»
                </div>
              ))}
              <div className="flex flex-wrap gap-1.5">
                {r.conflict.choices.map((c) => (
                  <button
                    key={c}
                    type="button"
                    disabled={chat.pending}
                    onClick={() => chat.resolveConflict(item, c)}
                    className="px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 border border-white/15 text-[11px] disabled:opacity-40"
                  >
                    {c === "message" ? "Use what I wrote" : "Use the selected location"}
                  </button>
                ))}
              </div>
            </div>
          )}

          {r && (r.citations ?? []).length > 0 && (
            <ol className="mt-2 space-y-0.5 text-[10px] text-[#a1a1aa]">
              {r.citations!.map((c) => (
                <li key={c.index} dir="auto">
                  <span className="text-[#60a5fa]">[{c.index}]</span>{" "}
                  {c.url && /^https?:\/\//i.test(c.url) ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" className="hover:underline text-[#93c5fd]">
                      {c.title || c.url}
                    </a>
                  ) : (
                    <span title={c.text}>{c.title || c.source_file || c.kind}</span>
                  )}
                  {c.provider ? <span className="opacity-70"> · {c.provider}</span> : null}
                </li>
              ))}
            </ol>
          )}

          {r && (r.limitations ?? []).length > 0 && (
            <details className="mt-2 text-[10px] text-[#a1a1aa]">
              <summary className="cursor-pointer text-[#d4d4d8]">Limitations</summary>
              <ul className="list-disc ps-4 mt-1 space-y-0.5">
                {r.limitations!.map((l, i) => (
                  <li key={i} dir="auto">
                    {l}
                  </li>
                ))}
              </ul>
            </details>
          )}

          {r && hasPanel && (
            <details className={`mt-2 rounded-lg border border-white/10 p-2 ${popup ? "" : "lg:hidden"}`}>
              <summary className="cursor-pointer text-[11px] text-[#d4d4d8]">Details</summary>
              <div className="mt-2">
                <PanelView panel={r.panel!} response={r} />
              </div>
            </details>
          )}

          {(dash || fc) && (
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              {dash && (
                <Link href={dash} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl cosmic-gold-button text-[11px] font-bold shadow-md hover:scale-[1.02] active:scale-95 transition-all">
                  Open in Dashboard →
                </Link>
              )}
              {fc && (
                <Link href={fc} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/15 text-[11px] font-semibold transition-all">
                  Open forecast →
                </Link>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export interface ChatBodyProps {
  chat: Chat;
  variant: "popup" | "page";
  placeholder?: string;
}

/** Message list + starter chips + input. Shared by the popup and the full page. */
export default function ChatBody({ chat, variant, placeholder }: ChatBodyProps) {
  const { items, pending, elapsed, starters, send } = chat;
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const popup = variant === "popup";

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items, pending]);

  const panelItem = (() => {
    if (popup) return null;
    const withPanel = items.filter((i) => i.response?.panel && i.response.panel.status === "ok");
    return withPanel.find((i) => i.id === picked) ?? withPanel[withPanel.length - 1] ?? null;
  })();

  const submit = (text: string) => {
    const t = text.trim();
    if (!t || pending) return;
    setInput("");
    send(t);
  };

  const list = (
    <div className={`flex-1 overflow-y-auto flex flex-col gap-3 ${popup ? "p-4" : "px-4 py-6"}`}>
      {items.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center text-xs text-[#a1a1aa] gap-3 py-4">
          <div className="w-14 h-14 rounded-2xl overflow-hidden border border-amber-400/40 bg-black shadow-[0_0_20px_rgba(245,158,11,0.25)] flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.jpg" alt="AI Ready" className="w-full h-full object-contain" />
          </div>
          <p className="font-bold text-white text-xs flex items-center gap-1.5">
            <span>AI Detective Ready</span>
            <span className="text-amber-400">✦</span>
          </p>
          <p className="text-[11px] text-slate-400 leading-relaxed max-w-[280px]">
            Ask about climate trends, forecasts, fires or methods. Answers use real NASA data and cite their sources.
          </p>
          <div className="flex flex-col gap-1.5 w-full max-w-md">
            {starters.map((s) => (
              <button
                key={s}
                type="button"
                disabled={pending}
                onClick={() => submit(s)}
                dir="auto"
                className="text-start px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] text-[#e4e4e7] transition-colors disabled:opacity-40"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        items.map((it) => (
          <Bubble key={it.id} item={it} chat={chat} variant={variant} active={panelItem?.id === it.id} onSelect={setPicked} />
        ))
      )}

      {pending && (
        <div className="flex items-center gap-2 p-2.5 rounded-xl bg-white/5 border border-white/10 text-xs text-[#a1a1aa] w-fit" role="status">
          <span className="w-1.5 h-1.5 rounded-full bg-[#60a5fa] animate-ping"></span>
          <span className="text-[11px]">Working... {elapsed}s{elapsed > 20 ? " (this can take up to ~90 s)" : ""}</span>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );

  const footer = (
    <footer className={`bg-white/5 border-t border-white/10 shrink-0 ${popup ? "p-3" : "p-4 bg-[#18181b]/75 backdrop-blur-xl"}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
        className={`flex items-center gap-2 ${popup ? "" : "max-w-3xl mx-auto"}`}
      >
        <input
          type="text"
          dir="auto"
          value={input}
          maxLength={1500}
          disabled={pending}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder ?? "Ask in any language..."}
          className="flex-1 bg-[#09090b]/80 backdrop-blur-md border border-white/15 focus:border-[#2563eb] rounded-xl px-3.5 py-2.5 text-xs text-[#f4f4f5] placeholder-[#71717a] outline-none transition-colors disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={!input.trim() || pending}
          aria-label="Send Message"
          className="px-4 py-2.5 rounded-xl cosmic-gold-button disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold transition-all flex items-center justify-center shrink-0 shadow-md active:scale-95"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </form>
    </footer>
  );

  if (popup) {
    return (
      <>
        {list}
        {footer}
      </>
    );
  }
  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 min-h-0 flex">
        <div className="flex-1 min-w-0 flex flex-col max-w-3xl w-full mx-auto lg:mx-0 lg:max-w-none lg:px-0">{list}</div>
        {panelItem?.response?.panel && (
          <aside className="hidden lg:block w-[420px] shrink-0 border-s border-white/10 bg-[#18181b]/60 overflow-y-auto p-4">
            <PanelView panel={panelItem.response.panel} response={panelItem.response} />
          </aside>
        )}
      </div>
      {footer}
    </div>
  );
}
