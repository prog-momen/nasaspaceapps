"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AssistantUnavailableError,
  fetchStarterExamples,
  loadSessionId,
  resetAssistantSession,
  saveSessionId,
  sendAssistantMessage,
} from "@/lib/assistant/client";
import { offlineReply } from "@/lib/assistant/fallback";
import { VARIABLES } from "@/lib/catalog";
import type { AssistantControls, AssistantLang, ChatItem } from "@/lib/assistant/types";

export interface SelectedPoint {
  lat: number;
  lon: number;
  name: string;
}

const ITEMS_KEY = "earthtrend.assistant.items";
const MAX_ITEMS = 40;
let counter = 0;
const newId = (p: string) => `${p}-${Date.now().toString(36)}-${++counter}`;
const timeNow = () => {
  const d = new Date();
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")} UTC`;
};

function pickLanguage(message: string): AssistantLang {
  if (/[؀-ۿ]/.test(message)) return "ar";
  if (/[A-Za-z]/.test(message)) return "en";
  return typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("ar") ? "ar" : "en";
}

function loadItems(): ChatItem[] {
  try {
    const raw = sessionStorage.getItem(ITEMS_KEY);
    return raw ? (JSON.parse(raw) as ChatItem[]) : [];
  } catch {
    return [];
  }
}
function storeItems(items: ChatItem[]) {
  try {
    sessionStorage.setItem(ITEMS_KEY, JSON.stringify(items.slice(-MAX_ITEMS)));
  } catch {
    /* quota or blocked storage: the conversation still works in memory */
  }
}

export const KNOWLEDGE_EXAMPLE = "What is the Mann-Kendall test?";
export const ARABIC_EXAMPLE = "هل ارتفعت درجة الحرارة في عمان بين 1990 و2024؟";

export function useAssistantChat(selected?: SelectedPoint | null) {
  const [items, setItems] = useState<ChatItem[]>([]);
  const [pending, setPending] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [starters, setStarters] = useState<string[]>([ARABIC_EXAMPLE, KNOWLEDGE_EXAMPLE]);
  const sidRef = useRef<string | null>(null);
  const pendingRef = useRef(false);
  const selectedRef = useRef(selected);
  useEffect(() => {
    selectedRef.current = selected;
  }, [selected]);

  // Restore conversation + session once on the client.
  useEffect(() => {
    sidRef.current = loadSessionId();
    const restored = loadItems();
    if (restored.length) setItems(restored);
  }, []);

  useEffect(() => {
    let alive = true;
    fetchStarterExamples().then((ex) => {
      if (!alive) return;
      const fromApi = ex.slice(0, 3).map((e) => {
        const v = VARIABLES.find((x) => x.key === e.variable_key)?.name.toLowerCase() ?? e.variable_key;
        return `Is ${v} changing in ${e.region_name} between ${e.start_year} and ${e.end_year}?`;
      });
      setStarters([...fromApi, ARABIC_EXAMPLE, KNOWLEDGE_EXAMPLE]);
    });
    return () => {
      alive = false;
    };
  }, []);

  // Elapsed-seconds counter while a turn runs.
  useEffect(() => {
    if (!pending) return;
    const t0 = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 500);
    return () => clearInterval(id);
  }, [pending]);

  const commit = useCallback((fn: (prev: ChatItem[]) => ChatItem[]) => {
    setItems((prev) => {
      const next = fn(prev);
      storeItems(next);
      return next;
    });
  }, []);

  const run = useCallback(
    async (message: string, choice?: "message" | "controls", prior?: AssistantControls) => {
      const text = message.trim();
      if (!text || pendingRef.current) return;
      pendingRef.current = true;
      setPending(true);
      setElapsed(0);
      const sel = selectedRef.current;
      const controls: AssistantControls = prior ?? {
        ...(sel ? { point: { lat: sel.lat, lon: sel.lon } } : {}),
        language: pickLanguage(text),
      };
      if (choice) {
        // The conflict reply is replaced by the re-sent turn.
        commit((prev) => {
          const i = prev.length - 1;
          return prev[i]?.response?.conflict ? prev.slice(0, i) : prev;
        });
      } else {
        commit((prev) => [...prev, { id: newId("u"), role: "user", text, time: timeNow() }]);
      }
      const ctl = new AbortController();
      const timer = setTimeout(() => ctl.abort(), 100_000);
      try {
        const r = await sendAssistantMessage({ message: text, sessionId: sidRef.current, controls, conflictChoice: choice, signal: ctl.signal });
        if (r.session_id) {
          sidRef.current = r.session_id;
          saveSessionId(r.session_id);
        }
        commit((prev) => [
          ...prev,
          { id: newId("a"), role: "assistant", text: r.answer ?? "", time: timeNow(), response: r, retryOf: { message: text, controls } },
        ]);
      } catch (e) {
        if (e instanceof AssistantUnavailableError) {
          const fb = await offlineReply(text, selectedRef.current);
          commit((prev) => [...prev, { id: newId("a"), role: "assistant", time: timeNow(), ...fb }]);
        } else {
          commit((prev) => [
            ...prev,
            { id: newId("e"), role: "assistant", time: timeNow(), error: true, text: e instanceof Error ? e.message : "Something went wrong." },
          ]);
        }
      } finally {
        clearTimeout(timer);
        pendingRef.current = false;
        setPending(false);
      }
    },
    [commit],
  );

  const send = useCallback((text: string) => run(text), [run]);

  const resolveConflict = useCallback(
    (item: ChatItem, choice: "message" | "controls") => {
      if (item.retryOf) run(item.retryOf.message, choice, item.retryOf.controls);
    },
    [run],
  );

  const reset = useCallback(async () => {
    if (pendingRef.current) return;
    const sid = sidRef.current;
    sidRef.current = null;
    saveSessionId(null);
    setItems([]);
    storeItems([]);
    if (sid) await resetAssistantSession(sid);
  }, []);

  return { items, pending, elapsed, starters, send, resolveConflict, reset };
}
