import type { AssistantResponse, SendArgs } from "./types";

export class AssistantUnavailableError extends Error {}
export class AssistantRequestError extends Error {}

const SID_KEY = "earthtrend.assistant.sid";

export function loadSessionId(): string | null {
  try {
    return sessionStorage.getItem(SID_KEY);
  } catch {
    return null;
  }
}
export function saveSessionId(id: string | null) {
  try {
    if (id) sessionStorage.setItem(SID_KEY, id);
    else sessionStorage.removeItem(SID_KEY);
  } catch {
    /* storage may be blocked */
  }
}

/** Sends one turn through the server proxy. 503 -> AssistantUnavailableError (caller may use the offline fallback). */
export async function sendAssistantMessage(a: SendArgs): Promise<AssistantResponse> {
  let res: Response;
  try {
    res = await fetch("/api/assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: a.message,
        session_id: a.sessionId ?? undefined,
        controls: a.controls,
        conflict_choice: a.conflictChoice,
      }),
      signal: a.signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new AssistantRequestError("The request was cancelled or timed out.");
    }
    throw new AssistantUnavailableError("Could not reach the server.");
  }
  const body = await res.json().catch(() => null);
  if (res.status === 503) throw new AssistantUnavailableError(body?.message ?? "AI service unavailable.");
  if (!res.ok || !body) {
    const detail = Array.isArray(body?.details) ? body.details.join(", ") : (body?.message ?? body?.error);
    throw new AssistantRequestError(detail ? String(detail) : `Request failed (HTTP ${res.status}).`);
  }
  return body as AssistantResponse;
}

export async function resetAssistantSession(sessionId: string): Promise<void> {
  try {
    await fetch("/api/assistant/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
  } catch {
    /* session may already be gone */
  }
}

export interface ExampleDef {
  title: string;
  story?: string;
  region_name: string;
  variable_key: string;
  start_year: number;
  end_year: number;
}

export async function fetchStarterExamples(): Promise<ExampleDef[]> {
  try {
    const res = await fetch("/api/examples");
    if (!res.ok) return [];
    const body = await res.json();
    return Array.isArray(body.examples) ? body.examples : [];
  } catch {
    return [];
  }
}
