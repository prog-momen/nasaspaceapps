// Response shapes of the Python AI service (/api/chat), as proxied by /api/assistant/chat.
export type AssistantLang = "ar" | "en";

export interface Artifact {
  type: string;
  title?: string;
  note?: string;
  [key: string]: unknown;
}

export interface Metric {
  label: string;
  value: string | number | null;
  unit?: string;
  tone?: string;
  basis?: string;
}

export interface Citation {
  index: number;
  kind?: string;
  title?: string;
  url?: string;
  provider?: string;
  text?: string;
  source_file?: string;
  section?: string;
}

export interface ResolvedLocation {
  name?: string;
  latitude: number;
  longitude: number;
}

export interface Resolved {
  location?: ResolvedLocation | null;
  period?: { start_year?: number; end_year?: number; start?: string; end?: string } | null;
  variable?: string | null;
}

export interface Panel {
  kind?: string;
  status?: string;
  title?: string;
  subtitle?: string;
  metrics?: Metric[];
  artifacts?: Artifact[];
  source?: {
    provider?: string;
    product?: string;
    live?: boolean;
    cache?: string;
    retrieved_at?: string;
    attribution?: string;
    links?: { label: string; url: string }[];
  };
  limitations?: string[];
}

export interface ConflictItem {
  field: string;
  message_value: unknown;
  controls_value: unknown;
}

export interface AssistantResponse {
  session_id: string;
  status: string;
  outcome?: string;
  language?: AssistantLang;
  answer: string;
  answer_source?: string;
  model?: string | null;
  tools?: { name: string; status?: string; provider?: string; product?: string }[];
  resolved?: Resolved | null;
  inline?: Artifact[];
  panel?: Panel | null;
  citations?: Citation[];
  warnings?: string[];
  conflict?: { items: ConflictItem[]; choices: ("message" | "controls")[] } | null;
  model_notice?: { kind?: string; text: string } | null;
  limitations?: string[];
  timing?: { total_ms?: number };
}

export interface AssistantControls {
  point?: { lat: number; lon: number };
  language?: AssistantLang;
}

export interface SendArgs {
  message: string;
  sessionId?: string | null;
  controls?: AssistantControls;
  conflictChoice?: "message" | "controls";
  signal?: AbortSignal;
}

/** One entry in the visible conversation. */
export interface ChatItem {
  id: string;
  role: "user" | "assistant";
  text: string;
  time: string;
  /** Present for real AI-service replies. */
  response?: AssistantResponse;
  /** Reply produced by the offline fallback (service unavailable). */
  offline?: boolean;
  /** Error bubble. */
  error?: boolean;
  /** Original user message + controls, kept so a conflict can be re-sent. */
  retryOf?: { message: string; controls?: AssistantControls };
  dashboardLink?: { lat: number; lon: number; name: string; variable: string };
}
