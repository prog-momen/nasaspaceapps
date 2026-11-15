"use strict";
/* EarthTrend Explorer local UI. Same-origin backend only; no credentials are ever handled here.
   Model/tool text is rendered ONLY through textContent / createElement (md() below): no HTML-string injection, no model-supplied HTML, links limited to http(s). */
const $ = (id) => document.getElementById(id);
const I18N = {
  ar: {subtitle: "بيانات حقيقية فقط — نموذج أولي محلي", newConv: "محادثة جديدة", send: "إرسال", sending: "جارٍ المعالجة…", placeholder: "اكتب سؤالك بأي لغة… (Enter للإرسال، Shift+Enter لسطر جديد)",
    tabChat: "💬 المحادثة", tabResults: "📊 النتائج", settings: "إعدادات التحليل (اختيارية)", settingsHint: "الأسئلة المكتوبة تعمل بدونها. ما تحدده هنا يُرسل مع كل رسالة؛ وإن اختلف عن نص الرسالة سأسألك.",
    task: "المهمة", variable: "المتغير", start: "من", end: "إلى", pick: "نقطة على الخريطة", box: "رسم مربع", clearLoc: "مسح الموقع",
    adv: "خيارات متقدمة", provider: "فهرس البيانات", mode: "وضع الإجابة", gibs: "طبقة GIBS (عرض فقط)", gibsDate: "تاريخ الطبقة", direct: "تشغيل الأداة مباشرة (بدون النموذج)",
    diag: "التشخيص", uiLang: "اللغة", locNone: "لا موقع محدد في الإعدادات.", pickHint: "انقر على الخريطة لاختيار نقطة.", boxHint: "انقر زاويتين على الخريطة لرسم مربع.",
    unit: "الوحدة", refs: "مراجع المنهجية (للطريقة فقط)", refsNote: "الأوراق مراجع للمنهج فقط وليست دليلًا على أي قيمة متوقعة؛ الأرقام من بيانات NASA POWER وتشغيل النموذج المسجَّل.", notRead: "لم يُقرأ النص الكامل محليًا", recolor: "غيّر لون الصندوق", retry: "إعادة المحاولة", dismiss: "إغلاق", conflictAsk: "اختر القيم التي تريد استخدامها:", useMsg: "استخدم ما في الرسالة", useCtl: "استخدم الإعدادات",
    noMap: "تعذّر تحميل مكتبة الخريطة (تحتاج إنترنت).", live: "مباشر", cache: "ذاكرة مؤقتة", show: "عرض التحليل", details: "تفاصيل تقنية", sources: "المصادر", limits: "حدود وتحذيرات", prov: "المصدر والتوقيت",
    empty: "اطرح سؤالًا ليظهر تحليله هنا: الخريطة والأرقام والرسوم والمصادر.", loading: "جارٍ جلب البيانات وتحليلها…", noAnalysis: "لا يوجد تحليل لهذه الرسالة", requested: "المكان المطلوب", footprint: "المنطقة الفعلية للبيانات",
    outcomes: {answered: "تمت الإجابة", zero_detections: "طلب صالح، صفر كشوف", no_data: "لا توجد بيانات مطابقة", unsupported: "غير مدعوم", needs_credentials: "يحتاج مفتاحًا", provider_outage: "المزود غير متاح", model_quota: "النموذج غير متاح", ambiguous: "يحتاج توضيحًا", insufficient_evidence: "أدلة غير كافية", pending: "المهمة قيد التنفيذ", error: "خطأ"},
    src: {claude: "Claude Haiku", glossary: "قاموس مدمج", web: "شرح من الويب", template: "قالب حتمي", rag_excerpts: "مقتطفات مسترجعة", none: ""}, by: {llm_tool_use: "فهم الطلب: Claude (Tool Use)", router: "فهم الطلب: موجّه حتمي", controls: "فهم الطلب: الإعدادات", follow_up: "فهم الطلب: متابعة"},
    tasks: {auto: "تلقائي (من الرسالة)", rag: "سؤال وثائقي", trend: "اتجاه تاريخي (NASA POWER)", weather_forecast: "توقع الطقس", weather_historical: "طقس تاريخي", fire_detections: "كشوف حرائق (FIRMS)", fire_danger: "خطر الحرائق", satellite_scenes: "مشاهد Sentinel", datasets: "مجموعات بيانات", land_surface_temperature: "حرارة سطح الأرض LST (AppEEARS)", forecast_monthly: "توقع إحصائي شهري (حتى 24 شهرًا)", fire_outlook: "توقع خطر الحرائق للشهر القادم (رسمي)", ndvi: "NDVI (Sentinel-2)"},
    vars: {auto: "تلقائي", air_temperature: "حرارة الهواء T2M", precipitation: "الهطول", relative_humidity: "الرطوبة النسبية", wind_speed: "سرعة الرياح", land_surface_temperature: "حرارة سطح الأرض"},
    examples: ["هل ارتفعت حرارة الهواء في نابلس بين 2005 و2025؟", "ما توقع الطقس في القاهرة للأيام الثلاثة القادمة؟", "في حرائق قريبة من القدس؟", "ما متوسط NDVI قرب نابلس آخر 60 يومًا؟", "توقع متوسط الحرارة الشهري في نابلس للسنتين القادمتين"]},
  en: {subtitle: "Real data only — local prototype", newConv: "New conversation", send: "Send", sending: "Working…", placeholder: "Ask in any language… (Enter to send, Shift+Enter for a new line)",
    tabChat: "💬 Chat", tabResults: "📊 Results", settings: "Analysis settings (optional)", settingsHint: "Typed questions work without these. Anything set here is sent with every message; if it differs from your text, I will ask.",
    task: "Task", variable: "Variable", start: "From", end: "To", pick: "Point on map", box: "Draw box", clearLoc: "Clear location",
    adv: "Advanced", provider: "Dataset catalog", mode: "Answer mode", gibs: "GIBS layer (display only)", gibsDate: "Layer date", direct: "Run tool directly (no model)",
    diag: "Diagnostics", uiLang: "Language", locNone: "No location in the settings.", pickHint: "Click the map to choose a point.", boxHint: "Click two corners on the map to draw a box.",
    unit: "unit", refs: "Method references (methods only)", refsNote: "Papers are method references, not evidence for any forecast value; numbers come from NASA POWER data and the recorded model run.", notRead: "full text not read locally", recolor: "Change box colour", retry: "Retry", dismiss: "Dismiss", conflictAsk: "Choose which values to use:", useMsg: "Use the message", useCtl: "Use the settings",
    noMap: "The map library could not load (needs internet).", live: "live", cache: "cache", show: "Show analysis", details: "Technical details", sources: "Sources", limits: "Limits & caveats", prov: "Source & timing",
    empty: "Ask a question and its analysis appears here: map, numbers, charts and sources.", loading: "Fetching and analysing the data…", noAnalysis: "No analysis for this message", requested: "Requested place", footprint: "Actual data footprint",
    outcomes: {answered: "Answered", zero_detections: "Valid query, zero detections", no_data: "No matching data", unsupported: "Unsupported", needs_credentials: "Needs a key", provider_outage: "Provider unavailable", model_quota: "Model unavailable", ambiguous: "Needs clarification", insufficient_evidence: "Insufficient evidence", pending: "Task running", error: "Error"},
    src: {claude: "Claude Haiku", glossary: "built-in glossary", web: "web explanation", template: "deterministic template", rag_excerpts: "retrieved excerpts", none: ""}, by: {llm_tool_use: "understood by Claude (Tool Use)", router: "understood by deterministic router", controls: "from settings", follow_up: "follow-up"},
    tasks: {auto: "Auto (from message)", rag: "Documentation question", trend: "Historical trend (NASA POWER)", weather_forecast: "Weather forecast", weather_historical: "Historical weather", fire_detections: "Fire detections (FIRMS)", fire_danger: "Fire danger", satellite_scenes: "Sentinel scenes", datasets: "Dataset discovery", land_surface_temperature: "Land surface temperature LST (AppEEARS)", forecast_monthly: "Monthly statistical forecast (up to 24 months)", fire_outlook: "Wildfire danger outlook, next month (official)", ndvi: "NDVI (Sentinel-2)"},
    vars: {auto: "auto", air_temperature: "Air temperature T2M", precipitation: "Precipitation", relative_humidity: "Relative humidity", wind_speed: "Wind speed", land_surface_temperature: "Land surface temperature"},
    examples: ["Has air temperature in Nablus risen between 2005 and 2025?", "What is the weather forecast for Cairo for the next 3 days?", "Are there fires near Jerusalem?", "What is the NDVI near Nablus for the last 60 days?", "Forecast the monthly mean temperature in Nablus for the next two years"]}
};
const OUT_ICON = {answered: "✔", zero_detections: "○", no_data: "∅", unsupported: "⛔", needs_credentials: "🔑", provider_outage: "⚠", model_quota: "⚠", ambiguous: "❓", insufficient_evidence: "∅", pending: "⏳", error: "✖"};
const OUT_TONE = {answered: "good", zero_detections: "", no_data: "warn", unsupported: "warn", needs_credentials: "warn", provider_outage: "warn", model_quota: "warn", ambiguous: "warn", insufficient_evidence: "warn", pending: "warn", error: "bad"};
const TONE_ICON = {hot: "▲", cold: "▼", warn: "⚠", good: "✔", bad: "✖"};
const S = {lang: localStorage.getItem("ui-lang") || "ar", sid: null, pending: false, turns: [], selected: null, point: null, bbox: null, mode: null, boxCorner: null, resultLayers: [], gibs: null, seq: 0};
const t = (k) => I18N[S.lang][k];

// ---------- helpers -------------------------------------------------------------------------------------------------
const el = (tag, attrs = {}, ...kids) => { const e = document.createElement(tag); for (const [k, v] of Object.entries(attrs)) { if (k === "class") e.className = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else if (v !== null && v !== undefined && v !== false) e.setAttribute(k, v); } for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c))); return e; };
function download(name, text, mime) { const a = el("a", {href: URL.createObjectURL(new Blob([text], {type: mime})), download: name}); document.body.append(a); a.click(); a.remove(); }
const csvCell = (v) => { const s = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
const toCsv = (cols, rows) => [cols, ...rows].map((r) => r.map(csvCell).join(",")).join("\n");
const nn = (k, v) => (v === null ? undefined : v);                       // JSON.stringify replacer: never show a literal null in details

// ---------- safe Markdown -> DOM (escape-by-construction) ---------------------------------------------------------------
function numSpans(text, host) {
  const re = /([+\-−]?\d+(?:[.,]\d+)*(?:\s?(?:°C|°|mm|km\/h|MW|%))?)/g; let last = 0, m;
  while ((m = re.exec(text))) { if (m.index > last) host.append(text.slice(last, m.index)); host.append(el("span", {class: "num"}, m[1])); last = re.lastIndex; }
  if (last < text.length) host.append(text.slice(last));
}
function inline(s, cites, host) {
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^)\s]+\)|\[\d{1,2}\]|\*[^*\s][^*]*\*)/g; let last = 0, m;
  while ((m = re.exec(s))) {
    if (m.index > last) numSpans(s.slice(last, m.index), host);
    const tok = m[1];
    if (tok.startsWith("**")) { const b = el("strong"); inline(tok.slice(2, -2), cites, b); host.append(b); }
    else if (tok.startsWith("`")) host.append(el("code", {}, tok.slice(1, -1)));
    else if (/^\[\d{1,2}\]$/.test(tok)) { const c = (cites || []).find((x) => x.index === +tok.slice(1, -1)); host.append(c ? el("button", {class: "cite", type: "button", title: c.title || "", onclick: () => showCitation(c)}, tok) : tok); }
    else if (tok.startsWith("[")) { const mm = /^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/.exec(tok); host.append(mm ? el("a", {href: mm[2], target: "_blank", rel: "noopener noreferrer"}, mm[1]) : tok); }
    else { const i = el("em"); inline(tok.slice(1, -1), cites, i); host.append(i); }
    last = re.lastIndex;
  }
  if (last < s.length) numSpans(s.slice(last), host);
}
// ---- callouts the reader can recolour (stored per message + callout in localStorage) ----------------------------------------------------------------
const CALLOUT = {key: "💡", warn: "⚠️", info: "ℹ️", good: "✅", hot: "🔥", cold: "❄️"};
const PALETTE = [["", "↺"], ["#0b5cad", "●"], ["#0b6e3f", "●"], ["#b26a00", "●"], ["#b3261e", "●"], ["#6b3fd4", "●"], ["#566574", "●"]];
const colorStore = () => { try { return JSON.parse(localStorage.getItem("calloutColors") || "{}"); } catch (e) { return {}; } };
const saveColor = (k, v) => { try { const s = colorStore(); if (v) s[k] = v; else delete s[k]; localStorage.setItem("calloutColors", JSON.stringify(s)); } catch (e) { /* storage may be blocked */ } };
function applyColor(box, c) { if (c) { box.dataset.custom = "1"; box.style.setProperty("--cc", c); } else { delete box.dataset.custom; box.style.removeProperty("--cc"); } }
function calloutNode(kind, key) {
  const box = el("div", {class: "callout " + kind, role: "note"}); const body = el("div", {class: "cbody", dir: "auto"});
  const pal = el("div", {class: "cpal", hidden: true}, PALETTE.map(([c, g]) => el("button", {type: "button", class: "sw-btn", title: c || "reset", style: c ? `color:${c}` : "", onclick: (e) => { e.stopPropagation(); applyColor(box, c); saveColor(key, c); pal.hidden = true; }}, g)));
  const tog = el("button", {type: "button", class: "cbtn", title: t("recolor"), "aria-label": t("recolor"), onclick: (e) => { e.stopPropagation(); pal.hidden = !pal.hidden; }}, "🎨");
  box.append(el("span", {class: "cico", "aria-hidden": "true"}, CALLOUT[kind] || "💡"), body, tog, pal); applyColor(box, colorStore()[key]);
  return {box, body};
}
function renderInlineArtifacts(list) {
  const w = el("div", {class: "inline-blocks"});
  list.forEach((a) => { const n = renderArtifact({...a}); if (n) { n.classList.add("in-chat"); w.append(n); if (a.note) n.append(el("div", {class: "hint"}, a.note)); } });
  return w;
}
function md(text, cites, opts = {}) {
  const root = el("div", {class: "md"}); const lines = String(text || "").replace(/\r/g, "").split("\n"); const inl = (opts.inline || []).map((a) => ({a, used: false}));
  let list = null, table = null, quote = null, cidx = 0;
  const place = (pred) => { const pick = inl.filter((x) => !x.used && pred(x.a)); pick.forEach((x) => (x.used = true)); if (pick.length) root.append(renderInlineArtifacts(pick.map((x) => x.a))); };
  const flush = () => { list = null; table = null; quote = null; };
  const isChart = (a) => a.type === "line_chart" || a.type === "forecast_chart" || a.type === "ensemble_chart";
  for (const raw of lines) {
    const line = raw.trimEnd(); let m; const tr = line.trim();
    if (!tr) { flush(); continue; }
    if ((m = /^\[\[(inline|chart|table)\]\]$/.exec(tr))) { flush(); place(m[1] === "inline" ? () => true : m[1] === "chart" ? isChart : (a) => a.type === "table"); continue; }
    if ((m = /^(#{1,3})\s+(.*)$/.exec(tr))) { flush(); const h = el("h" + m[1].length, {class: "md-h", dir: "auto"}); inline(m[2], cites, h); root.append(h); continue; }
    if ((m = /^\^\s*(.*)$/.exec(tr))) { flush(); const p = el("p", {class: "note", dir: "auto"}); inline(m[1], cites, p); root.append(p); continue; }
    if (tr.startsWith(">")) {
      const body = tr.replace(/^>\s?/, ""); const c = /^\[!(key|warn|info|good|hot|cold)\]\s*(.*)$/i.exec(body);
      if (c) { const n = calloutNode(c[1].toLowerCase(), `${opts.msgId || "m"}:${cidx++}`); inline(c[2], cites, n.body); root.append(n.box); quote = n.body; list = null; table = null; }
      else if (quote) { quote.append(el("br")); inline(body, cites, quote); }
      else { const q = el("blockquote", {dir: "auto"}); inline(body, cites, q); root.append(q); quote = q; }
      continue;
    }
    if (tr.startsWith("|")) {
      const cells = tr.replace(/^\||\|$/g, "").split("|").map((x) => x.trim());
      if (cells.every((x) => /^:?-{2,}:?$/.test(x))) continue;
      if (!table) { table = el("table", {class: "md-table"}); table.append(el("thead", {}, el("tr", {}, cells.map((x) => { const th = el("th"); inline(x, cites, th); return th; }))), el("tbody")); root.append(el("div", {class: "tablewrap"}, table)); }
      else table.tBodies[0].append(el("tr", {}, cells.map((x) => { const td = el("td"); inline(x, cites, td); return td; })));
      continue;
    }
    quote = null; table = null;
    if ((m = /^\s*(?:[-*•])\s+(.*)$/.exec(line)) || (m = /^\s*\d+[.)]\s+(.*)$/.exec(line))) {
      const ordered = /^\s*\d/.test(line);
      if (!list || list.tagName !== (ordered ? "OL" : "UL")) { list = el(ordered ? "ol" : "ul"); root.append(list); }
      const li = el("li", {dir: "auto"}); inline(m[1], cites, li); list.append(li); continue;
    }
    list = null; const p = el("p", {dir: "auto"}); inline(tr, cites, p); root.append(p);      // one idea per line -> one paragraph
  }
  place(() => true);                                                                          // inline artifacts the text did not place go at the end
  return root;
}

// ---------- i18n / static UI -----------------------------------------------------------------------------------------
function applyLang() {
  const L = S.lang; document.documentElement.lang = L; document.documentElement.dir = L === "ar" ? "rtl" : "ltr";
  const set = (id, v) => { $(id).textContent = v; };
  set("subtitle", t("subtitle")); set("btn-new", t("newConv")); set("sum-settings", t("settings")); set("settings-hint", t("settingsHint")); set("lbl-task", t("task")); set("lbl-variable", t("variable")); set("lbl-start", t("start")); set("lbl-end", t("end"));
  set("btn-pick", t("pick")); set("btn-box", t("box")); set("btn-clear-loc", t("clearLoc")); set("sum-adv", t("adv")); set("lbl-provider", t("provider")); set("lbl-mode", t("mode")); set("lbl-gibs", t("gibs")); set("lbl-gibs-date", t("gibsDate"));
  set("btn-direct", t("direct")); set("sum-diag", t("diag")); set("lbl-ui-lang", t("uiLang")); set("tab-chat", t("tabChat")); set("tab-results", t("tabResults"));
  $("input").placeholder = t("placeholder"); if (!S.pending) set("btn-send", t("send"));
  const fill = (id, map) => { const cur = $(id).value; $(id).replaceChildren(...Object.entries(map).map(([k, v]) => el("option", {value: k}, v))); $(id).value = cur || "auto"; };
  fill("c-task", t("tasks")); fill("c-variable", t("vars")); $("ui-lang").value = L;
  $("examples").replaceChildren(...t("examples").map((q) => el("button", {type: "button", onclick: () => send(q)}, q)));   // SAME pipeline as typed text: send(text)
  updateLocInfo(); renderResults();
}
function updateLocInfo() {
  const i = $("loc-info");
  if (S.bbox) i.textContent = `box: [${S.bbox.map((x) => x.toFixed(3)).join(", ")}]`;
  else if (S.point) i.textContent = `point: ${S.point.lat.toFixed(4)}, ${S.point.lon.toFixed(4)}`;
  else i.textContent = S.mode === "pick" ? t("pickHint") : S.mode === "box" ? t("boxHint") : t("locNone");
  $("c-lat").value = S.point ? S.point.lat.toFixed(4) : ""; $("c-lon").value = S.point ? S.point.lon.toFixed(4) : "";
}
function controls() {
  const c = {task: $("c-task").value, variable: $("c-variable").value === "auto" ? null : $("c-variable").value, provider: $("c-provider").value, answer_mode: $("c-mode").value, language: S.lang};
  const la = parseFloat($("c-lat").value), lo = parseFloat($("c-lon").value);
  if (S.bbox) c.bbox = S.bbox; else if (Number.isFinite(la) && Number.isFinite(lo)) c.point = {lat: la, lon: lo};
  if ($("c-start").value && $("c-end").value) { c.start = $("c-start").value; c.end = $("c-end").value; }
  return c;
}
function setView(v) { document.body.classList.toggle("view-chat", v === "chat"); document.body.classList.toggle("view-results", v === "results"); $("tab-chat").classList.toggle("on", v === "chat"); $("tab-results").classList.toggle("on", v === "results"); if (v === "results") setTimeout(() => { if (map) { map.invalidateSize(); applyMap(S.turns.find((x) => x.id === S.selected)); } }, 80); }

// ---------- map (one persistent Leaflet instance, moved into the results panel) -----------------------------------------
let map = null, selLayer = null; const mapEl = el("div", {class: "map", id: "map", role: "application", "aria-label": "map"});
function initMap() {
  if (typeof L === "undefined") { mapEl.textContent = t("noMap"); return; }
  map = L.map(mapEl, {worldCopyJump: true}).setView([30, 20], 3);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 18, attribution: "© OpenStreetMap contributors"}).addTo(map);
  map.on("click", (e) => {
    if (S.mode === "pick") { S.point = {lat: e.latlng.lat, lon: e.latlng.lng}; S.bbox = null; S.mode = null; drawSelection(); }
    else if (S.mode === "box") { if (!S.boxCorner) { S.boxCorner = e.latlng; } else { const a = S.boxCorner, b = e.latlng; S.bbox = [Math.min(a.lng, b.lng), Math.min(a.lat, b.lat), Math.max(a.lng, b.lng), Math.max(a.lat, b.lat)]; S.point = null; S.boxCorner = null; S.mode = null; drawSelection(); } }
    updateLocInfo();
  });
}
function drawSelection() {
  if (!map) return; if (selLayer) { map.removeLayer(selLayer); selLayer = null; }
  if (S.point) selLayer = L.circleMarker([S.point.lat, S.point.lon], {radius: 7, color: "#7b3fe4", dashArray: "3", fillOpacity: .15}).addTo(map).bindTooltip("settings point");
  else if (S.bbox) selLayer = L.rectangle([[S.bbox[1], S.bbox[0]], [S.bbox[3], S.bbox[2]]], {color: "#7b3fe4", dashArray: "4", fillOpacity: .05}).addTo(map);
}
function clearResultLayers() { if (!map) return; S.resultLayers.forEach((l) => map.removeLayer(l)); S.resultLayers = []; if (S.legendCtl) { map.removeControl(S.legendCtl); S.legendCtl = null; } }
/** Map legend for the forecast layer: colour swatch + text label (never colour alone). */
function mapLegend(a) {
  if (S.legendCtl) { map.removeControl(S.legendCtl); S.legendCtl = null; }
  const ctl = L.control({position: "bottomright"});
  ctl.onAdd = () => el("div", {class: "map-legend", role: "group", "aria-label": a.title || "legend"}, el("b", {}, "Forecast layer"), (a.legend || []).map((x) => el("div", {}, el("span", {class: "swatch", style: `background:${x.color}`}), " " + x.text)), el("div", {class: "obs-key"}, el("span", {class: "swatch obs"}), " Observed detections (not a forecast)"));
  ctl.addTo(map); S.legendCtl = ctl;
}
const addL = (l) => { l.addTo(map); S.resultLayers.push(l); return l; };
function addArtifactToMap(a) {
  if (a.type === "map_points") {
    const obs = a.layer_role === "observed";
    const g = L.featureGroup(a.points.map((p) => L.circleMarker([p.lat, p.lon], {radius: Math.max(4, Math.min(12, Math.sqrt((p.frp || 1)) * 1.4)), color: obs ? "#111" : "#c1121f", fillColor: obs ? "#ffb703" : "#c1121f", dashArray: obs ? "2" : null, fillOpacity: .7, weight: 1.5}).bindPopup(p.label)));
    addL(g); return g.getLayers().length ? g.getBounds() : null;
  } else if (a.type === "map_polygons") {
    const g = L.featureGroup(a.polygons.filter((p) => p.geometry).map((p) => L.geoJSON(p.geometry, {style: {color: p.color || "#0a4f8f", weight: p.color ? 1.5 : 1, fillColor: p.color || "#0a4f8f", fillOpacity: p.color ? .45 : .08}}).bindPopup(p.label)));
    addL(g); if (a.legend) mapLegend(a);
    return g.getLayers().length ? g.getBounds() : null;
  } else if (a.type === "wms_overlay") addL(L.tileLayer.wms(a.url, {layers: a.layers, format: a.format || "image/png", transparent: true, version: a.version || "1.3.0", opacity: .7, attribution: a.attribution || ""}));
  else if (a.type === "tile_overlay") addL(L.tileLayer(a.url, {maxNativeZoom: a.max_zoom || 7, maxZoom: 12, opacity: .85, attribution: a.attribution || "NASA GIBS"}));
  return null;
}
/** Sync the map with ONE turn: requested place (marker), actual data footprint (rectangle / model point), result geometry, and a caption. */
function applyMap(turn) {
  if (!map) return; clearResultLayers();
  const r = turn && turn.resp, m = r && r.map, cap = $("map-cap"); if (cap) cap.replaceChildren();
  if (!m || !r.panel || r.panel.status !== "ok") return;
  const q = m.requested; let bounds = null;
  if (!q.region) { const mk = addL(L.marker([q.lat, q.lon], {title: q.name})); mk.bindPopup(el("div", {}, el("b", {}, q.name), el("div", {}, `${q.lat}, ${q.lon}`))); }
  const fp = m.footprint;
  if (fp && (fp.type === "grid_cell" || fp.type === "query_bbox")) { const b = fp.bbox; const rc = addL(L.rectangle([[b[1], b[0]], [b[3], b[2]]], {color: fp.type === "grid_cell" ? "#0a4f8f" : "#c1121f", weight: 2, dashArray: "5", fillOpacity: .06}).bindTooltip(fp.label)); bounds = rc.getBounds(); }
  else if (fp && fp.type === "model_point") { addL(L.circleMarker(fp.point, {radius: 6, color: "#0a4f8f", fillOpacity: .5}).bindTooltip(fp.label)); bounds = L.latLngBounds([[q.lat, q.lon], fp.point]); }
  if (q.bbox) bounds = L.latLngBounds([[q.bbox[1], q.bbox[0]], [q.bbox[3], q.bbox[2]]]);
  (r.panel.artifacts || []).forEach((a) => { const b = addArtifactToMap(a); if (b && b.isValid() && a.layer_role !== "observed") bounds = b; });         // observed points never steer the view of a forecast
  const fit = () => { map.invalidateSize(); if (bounds && bounds.isValid()) map.fitBounds(bounds.pad(0.15), {maxZoom: m.scope === "point" ? 9 : 10}); else map.setView([q.lat, q.lon], m.scope === "point" ? 9 : 7); };
  fit(); setTimeout(fit, 300);                                  // the panel may still be laying out (tab switch / narrow layout): fit again once its size is final
  if (cap) cap.append(el("div", {}, el("b", {}, `${t("requested")}: `), `${q.name} (${q.lat}, ${q.lon})`), ...(fp ? [el("div", {}, el("b", {}, `${t("footprint")}: `), fp.label)] : []), ...(m.notes || []).map((n) => el("div", {}, "ⓘ " + n)));
}

// ---------- charts (canvas, no dependencies) --------------------------------------------------------------------------
function drawSeries(canvas, x, s, trend) {
  const dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight; canvas.width = w * dpr; canvas.height = h * dpr;
  const g = canvas.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
  const css = getComputedStyle(document.body), muted = css.getPropertyValue("--muted").trim() || "#888", line = css.getPropertyValue("--line").trim() || "#ccc", c2 = css.getPropertyValue("--brand2").trim() || "#0a4f8f", c1 = css.getPropertyValue("--brand").trim() || "#0b6e4f", hot = css.getPropertyValue("--hot").trim() || "#c1121f";
  const col = s.kind === "bar" ? c2 : c1;
  const ys = s.y.map((v) => (v === null || v === undefined ? NaN : +v)); let vals = ys.filter(Number.isFinite); if (trend) vals = vals.concat(trend.y);
  if (!vals.length) { g.fillStyle = muted; g.fillText("—", 10, 20); return; }
  let lo = Math.min(...vals), hi = Math.max(...vals); if (s.kind === "bar") lo = Math.min(0, lo); if (lo === hi) { lo -= 1; hi += 1; } const pad = (hi - lo) * .08; lo -= s.kind === "bar" && lo === 0 ? 0 : pad; hi += pad;
  const L0 = 46, R0 = 8, T0 = 8, B0 = 22, pw = w - L0 - R0, ph = h - T0 - B0, n = x.length;
  const X = (i) => L0 + (n === 1 ? pw / 2 : (i / (n - 1)) * pw), Y = (v) => T0 + (1 - (v - lo) / (hi - lo)) * ph;
  g.font = "11px system-ui"; g.strokeStyle = line; g.fillStyle = muted; g.lineWidth = 1;
  for (let k = 0; k <= 3; k++) { const v = lo + ((hi - lo) * k) / 3, y = Y(v); g.beginPath(); g.moveTo(L0, y); g.lineTo(w - R0, y); g.stroke(); g.textAlign = "right"; g.fillText(Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2), L0 - 4, y + 4); }
  g.textAlign = "center"; const ticks = Math.min(6, n); for (let k = 0; k < ticks; k++) { const i = ticks === 1 ? 0 : Math.round((k * (n - 1)) / (ticks - 1)); g.fillText(String(x[i]).slice(0, 10), Math.min(Math.max(X(i), L0 + 20), w - 30), h - 6); }
  if (s.kind === "bar") { const bw = Math.max(1, Math.min(14, (pw / n) * .7)); g.fillStyle = col; ys.forEach((v, i) => { if (Number.isFinite(v)) { const y0 = Y(0), y1 = Y(v); g.fillRect(X(i) - bw / 2, Math.min(y0, y1), bw, Math.abs(y1 - y0)); } }); }
  else { g.strokeStyle = col; g.lineWidth = 1.8; g.beginPath(); let pen = false; ys.forEach((v, i) => { if (!Number.isFinite(v)) { pen = false; return; } pen ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)); pen = true; }); g.stroke(); if (n <= 60) { g.fillStyle = col; ys.forEach((v, i) => { if (Number.isFinite(v)) { g.beginPath(); g.arc(X(i), Y(v), 2.6, 0, 7); g.fill(); } }); } }
  if (trend) { g.strokeStyle = hot; g.setLineDash([6, 4]); g.lineWidth = 1.8; g.beginPath(); g.moveTo(X(0), Y(trend.y[0])); g.lineTo(X(n - 1), Y(trend.y[1])); g.stroke(); g.setLineDash([]); }
}

/** Ensemble outlook: daily median line + p25-p75 and p10-p90 spread bands across members. Redraws whenever the canvas gets a size (e.g. when its tab becomes visible). */
function drawEnsemble(canvas, a) {
  const w = canvas.clientWidth, h = canvas.clientHeight; if (!w || !h) return;
  const dpr = window.devicePixelRatio || 1; canvas.width = w * dpr; canvas.height = h * dpr;
  const g = canvas.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
  const css = getComputedStyle(document.body), muted = css.getPropertyValue("--muted").trim() || "#888", line = css.getPropertyValue("--line").trim() || "#ccc", c1 = css.getPropertyValue("--brand").trim() || "#0b6e4f";
  const d = a.daily, n = a.dates.length, all = [].concat(d.p10, d.p90, d.median).filter(Number.isFinite);
  if (!all.length) { g.fillStyle = muted; g.fillText("—", 10, 20); return; }
  let lo = Math.min(0, ...all), hi = Math.max(...all); const pad = (hi - lo) * .08 || 1; hi += pad;
  const L0 = 46, R0 = 8, T0 = 8, B0 = 22, pw = w - L0 - R0, ph = h - T0 - B0;
  const X = (i) => L0 + (n === 1 ? pw / 2 : (i / (n - 1)) * pw), Y = (v) => T0 + (1 - (v - lo) / (hi - lo)) * ph;
  g.font = "11px system-ui"; g.strokeStyle = line; g.fillStyle = muted; g.lineWidth = 1; g.textAlign = "right";
  for (let k = 0; k <= 3; k++) { const v = lo + ((hi - lo) * k) / 3, y = Y(v); g.beginPath(); g.moveTo(L0, y); g.lineTo(w - R0, y); g.stroke(); g.fillText(v.toFixed(1), L0 - 4, y + 4); }
  g.textAlign = "center"; const ticks = Math.min(6, n); for (let k = 0; k < ticks; k++) { const i = ticks === 1 ? 0 : Math.round((k * (n - 1)) / (ticks - 1)); g.fillText(String(a.dates[i]).slice(5, 10), Math.min(Math.max(X(i), L0 + 16), w - 22), h - 6); }
  const band = (top, bot, alpha) => { g.fillStyle = c1; g.globalAlpha = alpha; g.beginPath(); top.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)))); for (let i = n - 1; i >= 0; i--) g.lineTo(X(i), Y(bot[i])); g.closePath(); g.fill(); g.globalAlpha = 1; };
  band(d.p90, d.p10, .15); band(d.p75, d.p25, .3);
  g.strokeStyle = c1; g.lineWidth = 2; g.beginPath(); d.median.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)))); g.stroke();
}

/** History (solid) + forecast (dashed, different colour) + 80% / 95% prediction-interval bands + a cutoff marker. Values are never smoothed or clipped here. */
function drawForecast(canvas, a) {
  const dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight; canvas.width = w * dpr; canvas.height = h * dpr;
  const g = canvas.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
  const css = getComputedStyle(document.body), muted = css.getPropertyValue("--muted").trim() || "#888", line = css.getPropertyValue("--line").trim() || "#ccc", c1 = css.getPropertyValue("--brand").trim() || "#0b6e4f", c2 = css.getPropertyValue("--hot").trim() || "#c1121f", c3 = css.getPropertyValue("--brand2").trim() || "#0a4f8f";
  const hx = a.history.x, hy = a.history.y, fx = a.forecast.x, fy = a.forecast.y, n = hx.length + fx.length;
  const all = [...hy, ...fy, ...a.forecast.lo95.filter((v) => v !== null), ...a.forecast.hi95.filter((v) => v !== null)].filter(Number.isFinite);
  let lo = Math.min(...all), hi = Math.max(...all); const pad = (hi - lo) * .06 || 1; lo -= pad; hi += pad;
  const L0 = 46, R0 = 8, T0 = 10, B0 = 22, pw = w - L0 - R0, ph = h - T0 - B0;
  const X = (i) => L0 + (i / (n - 1)) * pw, Y = (v) => T0 + (1 - (v - lo) / (hi - lo)) * ph, off = hx.length;
  g.font = "11px system-ui"; g.strokeStyle = line; g.fillStyle = muted; g.lineWidth = 1;
  for (let k = 0; k <= 3; k++) { const v = lo + ((hi - lo) * k) / 3, y = Y(v); g.beginPath(); g.moveTo(L0, y); g.lineTo(w - R0, y); g.stroke(); g.textAlign = "right"; g.fillText(Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1), L0 - 4, y + 4); }
  const xs = [...hx, ...fx]; g.textAlign = "center"; for (let k = 0; k < 6; k++) { const i = Math.round((k * (n - 1)) / 5); g.fillText(String(xs[i]).slice(0, 7), Math.min(Math.max(X(i), L0 + 22), w - 26), h - 6); }
  const band = (loA, hiA, color, alpha) => { g.fillStyle = color; g.globalAlpha = alpha; g.beginPath(); let first = true; fx.forEach((_, i) => { if (hiA[i] === null) return; const x = X(off + i); first ? g.moveTo(x, Y(hiA[i])) : g.lineTo(x, Y(hiA[i])); first = false; });
    for (let i = fx.length - 1; i >= 0; i--) { if (loA[i] !== null) g.lineTo(X(off + i), Y(loA[i])); } g.closePath(); g.fill(); g.globalAlpha = 1; };
  band(a.forecast.lo95, a.forecast.hi95, c3, .16); band(a.forecast.lo80, a.forecast.hi80, c3, .28);
  g.strokeStyle = c1; g.lineWidth = 1.7; g.beginPath(); hy.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)))); g.stroke();
  g.strokeStyle = c2; g.lineWidth = 2; g.setLineDash([6, 4]); g.beginPath(); fy.forEach((v, i) => { if (v === null) return; i ? g.lineTo(X(off + i), Y(v)) : g.moveTo(X(off + i), Y(v)); }); g.stroke(); g.setLineDash([]);
  const cx = X(off - 0.5); g.strokeStyle = muted; g.setLineDash([2, 3]); g.beginPath(); g.moveTo(cx, T0); g.lineTo(cx, T0 + ph); g.stroke(); g.setLineDash([]); g.fillStyle = muted; g.textAlign = "right"; g.fillText("cutoff " + String(a.cutoff).slice(0, 7), cx - 4, T0 + 10);
}
function renderArtifact(a) {
  const box = el("div", {class: "artifact"}); if (a.title) box.append(el("h4", {dir: "auto"}, a.title));
  if (a.type === "forecast_chart") {
    const c = el("canvas", {class: "chart tall", role: "img", "aria-label": a.title}); box.append(c); requestAnimationFrame(() => drawForecast(c, a));
    const L = a.legend || {}; box.append(el("div", {class: "legend"}, el("span", {class: "sw hist"}), L.history || "history", " · ", el("span", {class: "sw fc"}), L.forecast || "forecast", " · ", el("span", {class: "sw b80"}), L.band80 || "80%", " · ", el("span", {class: "sw b95"}), L.band95 || "95%"),
      el("div", {class: "hint"}, `${t("unit")}: ${a.unit} · cutoff ${a.cutoff}`));
    return box;
  }
  if (a.type === "line_chart") {
    a.series.forEach((s) => { box.append(el("div", {class: "series-label"}, `${s.name}${s.unit ? " (" + s.unit + ")" : ""}`)); const c = el("canvas", {class: "chart", role: "img", "aria-label": `${a.title} ${s.name}`}); box.append(c); requestAnimationFrame(() => drawSeries(c, a.x, s, a.series.length === 1 ? a.trend_line : null)); });
    if (a.trend_line) box.append(el("div", {class: "hint"}, "- - - " + a.trend_line.label));
  } else if (a.type === "table") {
    const tb = el("table", {class: "data"}, el("thead", {}, el("tr", {}, a.columns.map((c) => el("th", {}, c)))), el("tbody", {}, a.rows.slice(0, 200).map((r) => el("tr", {}, r.map((v) => el("td", {}, v === null || v === undefined ? "" : String(v)))))));
    box.append(el("div", {class: "tablewrap"}, tb), el("div", {class: "dl"}, el("button", {class: "btn small", type: "button", onclick: () => download((a.title || "table").replace(/\W+/g, "_") + ".csv", toCsv(a.columns, a.rows), "text/csv")}, "CSV ⬇"), a.rows.length > 200 ? el("span", {class: "hint"}, `200 / ${a.rows.length} (CSV has all)`) : null));
  } else if (a.type === "scenes") {
    box.append(el("div", {class: "scenes"}, a.scenes.map((s) => el("div", {class: "scene"}, s.preview ? el("img", {src: s.preview, alt: s.id, loading: "lazy", onerror: (e) => { e.target.replaceWith(el("div", {class: "noimg"}, "—")); }}) : el("div", {class: "noimg"}, "—"),
      el("div", {}, el("b", {}, (s.datetime || "").slice(0, 10)), ` · ${s.cloud_cover_percent ?? "?"}% ☁`, s.id ? el("div", {class: "hint"}, String(s.id).slice(0, 38)) : null)))));
  } else if (a.type === "category_strip") {
    const strip = el("div", {class: "cat-strip", role: "list"}, a.cells.map((c) => {
      const mixed = c.mixed ? " · " + Object.entries(c.shares).map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(" / ") : "";
      return el("div", {class: "cat-cell", role: "listitem", style: `background:${c.color}`, title: c.text + mixed}, el("div", {class: "cm"}, c.label), el("div", {class: "ct"}, c.text), c.mixed ? el("div", {class: "cs"}, mixed.slice(3)) : null);
    }));
    box.append(strip, el("div", {class: "legend cat-legend"}, (a.legend || []).map((x) => el("span", {}, el("span", {class: "swatch", style: `background:${x.color}`}), " " + x.text + "  "))));
  } else if (a.type === "ensemble_chart") {
    const c = el("canvas", {class: "chart tall", role: "img", "aria-label": a.title}); box.append(c);
    requestAnimationFrame(() => drawEnsemble(c, a));
    if (window.ResizeObserver) new ResizeObserver(() => drawEnsemble(c, a)).observe(c);
    box.append(el("div", {class: "hint"}, `${a.unit || ""} · ${a.title ? "" : ""}line = median across members; dark band = p25–p75, light band = p10–p90 (spread, not a calibrated uncertainty)`));
  } else if (a.type === "map_points") {
    box.append(el("div", {class: "hint"}, a.layer_role === "observed" ? `🟡 ${a.points.length} OBSERVED detections — shown on the map (not a forecast)` : `🗺 ${a.points.length} points — shown on the map`));
    if (a.points.length) box.append(el("div", {class: "dl"}, el("button", {class: "btn small", type: "button", onclick: () => download("detections.geojson", JSON.stringify({type: "FeatureCollection", features: a.points.map((p) => ({type: "Feature", geometry: {type: "Point", coordinates: [p.lon, p.lat]}, properties: {label: p.label, frp_mw: p.frp}}))}), "application/geo+json")}, "GeoJSON ⬇")));
  } else return null;
  return box;
}

// ---------- results panel ---------------------------------------------------------------------------------------------
function metricNode(m) {
  const val = m.value === null || m.value === undefined ? "—" : String(m.value); const tone = m.tone && m.tone !== "neutral" ? m.tone : "";
  return el("div", {class: "metric " + tone, title: m.basis || ""}, el("div", {class: "l"}, m.label),
    el("div", {class: "v"}, tone && TONE_ICON[tone] ? TONE_ICON[tone] + " " : "", val, m.unit ? el("span", {class: "u"}, " " + m.unit) : null), m.basis && tone ? el("div", {class: "b"}, m.basis) : null);
}
function renderResults() {
  const host = $("results"); const turn = S.turns.find((x) => x.id === S.selected);
  if (S.pending && turn && !turn.resp) { host.replaceChildren(el("div", {class: "state"}, el("div", {class: "spinner"}), el("div", {}, t("loading")))); return; }
  if (!turn || !turn.resp) { clearResultLayers(); host.replaceChildren(el("div", {class: "state"}, el("div", {style: "font-size:34px"}, "🌍"), el("div", {}, t("empty")))); return; }
  const r = turn.resp, p = r.panel || {}; const oc = r.outcome || "error";
  if (p.status !== "ok") {     // failed / unsupported / clarification: NEVER show the data or map of an earlier turn here
    clearResultLayers();
    host.replaceChildren(el("div", {class: "state"}, el("div", {style: "font-size:30px"}, OUT_ICON[oc] || "ⓘ"), el("b", {}, t("noAnalysis")), el("span", {class: "chip " + (OUT_TONE[oc] || "")}, `${OUT_ICON[oc] || ""} ${t("outcomes")[oc] || oc}`),
      el("div", {class: "hint", dir: "auto"}, `“${turn.user.slice(0, 120)}”`)));
    return;
  }
  const kids = [el("div", {class: "res-head"}, el("h2", {dir: "auto"}, p.title || ""), p.subtitle ? el("div", {class: "sub", dir: "auto"}, p.subtitle) : null)];
  if (r.map) kids.push(mapEl, el("div", {class: "map-cap", id: "map-cap"}));
  if (p.metrics && p.metrics.length) kids.push(el("div", {class: "metrics"}, p.metrics.map(metricNode)));
  (p.artifacts || []).forEach((a) => { const n = renderArtifact(a); if (n) kids.push(n); });
  if (p.citations && p.citations.length) kids.push(el("div", {class: "artifact"}, el("h4", {}, t("sources")), p.citations.map((c) => el("div", {}, el("button", {class: "cite", type: "button", onclick: () => showCitation(c)}, `[${c.index}]`), ` ${c.title || c.source_file} › ${c.section || ""}`))));
  if ((p.references || []).length) kids.push(el("details", {class: "prov"}, el("summary", {}, t("refs")), el("div", {class: "hint"}, t("refsNote")), el("ul", {}, p.references.map((r) => el("li", {dir: "auto"}, `${(r.authors || []).slice(0, 2).join(", ")}${(r.authors || []).length > 2 ? " et al." : ""} (${r.year ?? "n/a"}). ${r.title}. `, r.doi ? el("a", {href: "https://doi.org/" + r.doi, target: "_blank", rel: "noopener noreferrer"}, "doi:" + r.doi) : el("a", {href: r.url, target: "_blank", rel: "noopener noreferrer"}, "link"), r.full_text_read ? "" : " · " + t("notRead"))))));
  const s = p.source || {};
  kids.push(el("div", {class: "prov"}, el("b", {}, t("prov")), el("div", {}, [s.provider, s.product].filter(Boolean).join(" · "), s.live === true ? ` · ${t("live")}` : s.cache ? ` · ${t("cache")}: ${s.cache}` : "", s.retrieved_at ? ` · ${s.retrieved_at.slice(0, 16).replace("T", " ")}Z` : ""),
    (s.links || []).length ? el("div", {}, s.links.map((l) => el("a", {href: l.url, target: "_blank", rel: "noopener noreferrer", style: "margin-inline-end:10px"}, l.label))) : null, s.attribution ? el("div", {}, s.attribution) : null));
  if ((p.limitations || []).length) kids.push(el("details", {class: "prov"}, el("summary", {}, t("limits")), el("ul", {}, p.limitations.map((x) => el("li", {dir: "auto"}, x)))));
  if (r.raw_result) kids.push(el("div", {class: "dl"}, el("button", {class: "btn small", type: "button", onclick: () => download("result.json", JSON.stringify(r.raw_result, null, 2), "application/json")}, "JSON ⬇")));
  host.replaceChildren(...kids);
  applyMap(turn);
}
function selectTurn(id, switchTab) { S.selected = id; document.querySelectorAll(".msg.assistant").forEach((m) => m.classList.toggle("sel", m.dataset.id === String(id))); renderResults(); if (switchTab && window.matchMedia("(max-width:980px)").matches) setView("results"); }

// ---------- messages --------------------------------------------------------------------------------------------------
function showCitation(c) {
  const b = $("modal-body"); b.replaceChildren(el("h3", {dir: "auto"}, `[${c.index}] ${c.title || c.source_file || ""}`), el("div", {class: "hint"}, [c.source_file, c.section, c.service_id, c.score ? "score " + c.score : null, c.retrieved_at ? "retrieved " + c.retrieved_at : null].filter(Boolean).join(" › ")),
    c.url && /^https?:/.test(c.url) ? el("a", {href: c.url, target: "_blank", rel: "noopener noreferrer"}, c.url) : null, el("pre", {dir: "auto"}, c.text || ""));
  $("modal").hidden = false;
}
function addUser(text) { const m = el("div", {class: "msg user"}, el("div", {dir: "auto"}, text)); $("messages").append(m); m.scrollIntoView({block: "end"}); }
const chip = (text, cls = "", title = "") => el("span", {class: "chip " + cls, title}, text);
function addAssistant(turn) {
  const r = turn.resp; const m = el("div", {class: "msg assistant", "data-id": turn.id}); m.append(el("div", {class: "avatar", "aria-hidden": "true"}, "🌍")); const content = el("div", {class: "content"}); m.append(content); content.append(md(r.answer || "", r.citations || [], {msgId: turn.id, inline: r.inline || []}));
  const oc = r.outcome || "error"; const chips = el("div", {class: "chips"});
  chips.append(chip(`${OUT_ICON[oc] || ""} ${t("outcomes")[oc] || oc}`, OUT_TONE[oc] || ""));
  const srcLab = t("src")[r.answer_source]; if (srcLab) chips.append(chip(srcLab + (r.model && r.answer_source === "claude" ? ` · ${r.model}` : ""), "model", t("by")[r.selected_by] || ""));
  if (r.model_notice) chips.append(chip("⚠ " + r.model_notice.text, "warn"));
  ((r.panel || {}).metrics || []).filter((x) => x.tone && x.tone !== "neutral").slice(0, 2).forEach((x) => chips.append(chip(`${TONE_ICON[x.tone] || ""} ${x.label}: ${x.value}${x.unit ? " " + x.unit : ""}`, x.tone, x.basis || "")));
  content.append(chips);
  if (r.conflict) content.append(el("div", {class: "conflict"}, t("conflictAsk"), r.conflict.items.map((i) => el("div", {}, `${i.field}: «${i.message_value}» ⟷ «${i.controls_value}»`)),
    el("div", {class: "row"}, el("button", {class: "btn small", type: "button", onclick: () => send(turn.user, "message")}, t("useMsg")), el("button", {class: "btn small", type: "button", onclick: () => send(turn.user, "controls")}, t("useCtl")))));
  if ((r.panel || {}).status === "ok") content.append(el("div", {class: "msg-actions"}, el("button", {class: "btn small", type: "button", onclick: () => selectTurn(turn.id, true)}, "📊 " + t("show"))));
  const dg = {decision: r.decision, understood_by: r.selected_by, tools: r.tools, fallback_reason: r.fallback_reason, answer_source: r.answer_source, warnings: r.warnings, timing_ms: (r.timing || {}).total_ms, outcome: r.outcome, status: r.status};
  content.append(el("details", {class: "diagbox"}, el("summary", {}, t("details")), el("pre", {}, JSON.stringify(dg, nn, 1))));
  m.addEventListener("click", (e) => { if (!e.target.closest("button,a,summary,details")) selectTurn(turn.id, false); });
  $("messages").append(m); m.scrollIntoView({block: "end"});
}

// ---------- sending ---------------------------------------------------------------------------------------------------
function setPending(p) { S.pending = p; $("btn-send").disabled = p; $("input").disabled = p; $("btn-send").textContent = p ? t("sending") : t("send"); $("btn-direct").disabled = p; }
function showBanner(msg, retry) { const b = $("banner"); b.replaceChildren(el("span", {}, msg), el("span", {class: "row"}, retry ? el("button", {class: "btn small", type: "button", onclick: retry}, t("retry")) : null, el("button", {class: "btn small", type: "button", onclick: () => (b.hidden = true)}, t("dismiss")))); b.hidden = false; }
async function api(path, body, method = "POST") {
  const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 150000);
  try { const r = await fetch(path, {method, headers: {"Content-Type": "application/json"}, body: body ? JSON.stringify(body) : undefined, signal: ctl.signal}); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail ? (typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail)) : `HTTP ${r.status}`); return j; } finally { clearTimeout(timer); }
}
/** The ONE submit path: typed text and example buttons both call this with just the message text. */
async function send(message, choice = null) {
  if (S.pending) return; message = (message || "").trim(); if (!message) return; $("banner").hidden = true;
  let turn = choice ? S.turns[S.turns.length - 1] : null;
  if (!turn) { turn = {id: ++S.seq, user: message, resp: null}; S.turns.push(turn); addUser(message); } else { turn.resp = null; }
  const prevSelected = S.selected; S.selected = turn.id; setPending(true); renderResults();
  try {
    const r = await api("/api/chat", {message, session_id: S.sid, controls: controls(), conflict_choice: choice}); S.sid = r.session_id; sessionStorage.setItem("sid", S.sid);
    turn.resp = r; if (choice) document.querySelector(`.msg.assistant[data-id="${turn.id}"]`)?.remove(); addAssistant(turn); if (!choice) $("input").value = "";
    const explanation = r.status === "ok" && (!r.panel || r.panel.kind === "none");            // glossary / documentation / web answers carry no analysis: keep the previous analysis in the panel
    if (explanation && prevSelected) { S.selected = prevSelected; selectTurn(prevSelected, false); } else selectTurn(turn.id, r.panel && r.panel.status === "ok");
  } catch (e) { S.turns = S.turns.filter((x) => x !== turn || x.resp); S.selected = (S.turns[S.turns.length - 1] || {}).id || null; showBanner(`${e.name === "AbortError" ? "timeout" : e.message}`, () => send(message, choice)); renderResults(); }
  finally { setPending(false); $("input").focus(); }
}
async function newConversation() {
  if (S.pending) return; if (S.sid) { try { await api("/api/chat/reset", {session_id: S.sid}); } catch (e) { /* session may already be gone */ } }
  S.sid = null; S.turns = []; S.selected = null; sessionStorage.removeItem("sid"); $("messages").replaceChildren(); $("banner").hidden = true; $("input").value = ""; renderResults();
}
async function runDirect() {
  if (S.pending) return; const task = $("c-task").value; const map_ = {trend: "analyze_trend", weather_forecast: "get_weather", weather_historical: "get_weather", fire_detections: "get_fire_detections", fire_danger: "list_fire_danger", satellite_scenes: "search_satellite_scenes", datasets: "search_earth_datasets", land_surface_temperature: "get_lst", ndvi: "get_ndvi", forecast_monthly: "forecast_monthly", fire_outlook: "forecast_fire_danger"};
  if (!map_[task]) { showBanner(t("task") + ": " + t("tasks").trend + " …", null); return; }
  const args = task === "weather_historical" ? {mode: "historical"} : task === "weather_forecast" ? {mode: "forecast"} : task === "datasets" ? {keyword: ($("input").value || "land surface temperature").slice(0, 60)} : {};
  if (task === "trend") { const v = $("c-variable").value; args.variable = v === "auto" ? "air_temperature" : v; }
  setPending(true); const turn = {id: ++S.seq, user: `▶ ${map_[task]}`, resp: null}; S.turns.push(turn); addUser(turn.user);
  try { const r = await api("/api/tools/" + map_[task], {args, controls: controls(), language: S.lang});
    turn.resp = {answer: r.answer, answer_source: "template", outcome: r.status === "ok" ? "answered" : "no_data", status: r.status, selected_by: "controls", citations: [], panel: {kind: map_[task], status: r.status === "ok" ? "ok" : "error", title: map_[task], subtitle: "direct", metrics: [], artifacts: r.artifacts, source: {provider: r.result.provider, product: r.result.product, live: r.result.live, cache: r.result.cache, retrieved_at: r.result.retrieved_at, attribution: r.result.attribution, links: (r.result.source_links || []).map((u) => ({label: u.split("//")[1].split("/")[0], url: u}))}, limitations: r.result.limitations || []}, raw_result: r.result, tools: [{name: r.tool, status: r.status}], warnings: []};
    addAssistant(turn); selectTurn(turn.id, true); }
  catch (e) { showBanner(e.message, runDirect); S.turns.pop(); } finally { setPending(false); }
}

// ---------- diagnostics -----------------------------------------------------------------------------------------------
async function loadDiag() {
  const body = $("diag-body"); body.textContent = "…";
  try {
    const d = await api("/api/diagnostics", null, "GET");
    const row = (a, b) => el("tr", {}, el("td", {}, a), el("td", {}, b)); const tb = el("table", {});
    tb.append(row("backend", `${d.backend.status} · python ${d.backend.python} · sessions ${d.backend.sessions}`), row("model", `${d.model.configured} (fallbacks: ${d.model.fallbacks.join(", ") || "none"}) · key ${d.model.api_key_configured ? "present" : "MISSING"}`),
      row("model usage today (local count)", Object.entries(d.model.usage_today.models || {}).map(([m, v]) => `${m}: ${v.requests}`).join(" · ") || "0"), row("exhausted (s until retry)", JSON.stringify(d.model.exhausted_for_seconds)),
      row("knowledge index", `${d.knowledge_index.ready ? "ready" : "empty"} ${JSON.stringify(d.knowledge_index.collections)}`), row("paths", `${d.backend.project_dir} · data ${d.backend.data_dir} · log ${d.backend.log_file}`));
    const pt = el("table", {}, el("thead", {}, el("tr", {}, ["provider", "capabilities", "config", "last test", ""].map((h) => el("th", {}, h)))));
    d.providers.forEach((p) => { const lt = p.last_test; pt.append(el("tr", {}, el("td", {}, el("a", {href: p.links[0], target: "_blank", rel: "noopener noreferrer"}, p.name), el("div", {class: "hint"}, p.coverage)), el("td", {}, p.capabilities.join(", ")),
      el("td", {}, p.configuration, p.auth.length ? el("div", {class: "hint"}, "creds: " + Object.entries(p.credentials_present).map(([k, v]) => `${k}=${v ? "set" : "missing"}`).join(" ")) : null, p.setup ? el("div", {class: "hint"}, "register: " + p.setup.register) : null),
      el("td", {}, lt ? `${lt.status}${lt.reason_code ? " (" + lt.reason_code + ")" : ""} ${lt.live ? "live" : lt.cache || ""} ${lt.seconds ?? ""}s @ ${(lt.tested_at || "").slice(11, 16)}Z` : "—"),
      el("td", {}, el("button", {class: "btn small", type: "button", onclick: async (e) => { e.target.disabled = true; try { await api("/api/diagnostics/test/" + p.id, {}); } catch (x) { /* shown after reload */ } loadDiag(); }}, "test"),
        ...Object.entries(p.extra_tests || {}).map(([id, r]) => el("div", {class: "hint"}, el("button", {class: "btn small", type: "button", onclick: async (e) => { e.target.disabled = true; try { await api("/api/diagnostics/test/" + id, {}); } catch (x) { /* shown after reload */ } loadDiag(); }}, id), r ? ` ${r.status}${r.reason_code ? " (" + r.reason_code + ")" : ""} @ ${(r.tested_at || "").slice(11, 16)}Z` : " —"))))); });
    body.replaceChildren(tb, el("h4", {}, "providers"), pt, el("div", {class: "row"}, el("button", {class: "btn small", type: "button", onclick: async (e) => { if (!confirm("This sends ONE request to claude-haiku-5-5 (uses API credit). Continue?")) return; e.target.disabled = true; try { await api("/api/diagnostics/test/claude", {}); } catch (x) {} loadDiag(); }}, "Claude test (1 request)"),
      el("button", {class: "btn small", type: "button", onclick: loadDiag}, "refresh")), el("div", {class: "hint"}, d.model.note));
  } catch (e) { body.textContent = "diagnostics error: " + e.message; }
}

// ---------- boot ------------------------------------------------------------------------------------------------------
async function loadGibs() {
  try { const g = await api("/api/gibs/layers", null, "GET"); const sel = $("c-gibs"); Object.entries(g.layers).forEach(([k, v]) => sel.append(el("option", {value: k}, v.title))); $("c-gibs-date").value = new Date(Date.now() - 3 * 864e5).toISOString().slice(0, 10); } catch (e) { /* optional */ }
  $("c-gibs").addEventListener("change", showGibs); $("c-gibs-date").addEventListener("change", showGibs);
}
async function showGibs() {
  if (!map) return; if (S.gibs) { map.removeLayer(S.gibs); S.gibs = null; } const layer = $("c-gibs").value; if (!layer) return;
  try { const r = await api(`/api/gibs/overlay?layer=${encodeURIComponent(layer)}&date=${$("c-gibs-date").value}`, null, "GET"); S.gibs = L.tileLayer(r.artifact.url, {maxNativeZoom: r.artifact.max_zoom, maxZoom: 12, opacity: .85, attribution: "NASA GIBS"}).addTo(map); } catch (e) { showBanner("GIBS: " + e.message, null); }
}
document.addEventListener("DOMContentLoaded", () => {
  initMap(); applyLang(); loadGibs();
  $("ui-lang").addEventListener("change", (e) => { S.lang = e.target.value; localStorage.setItem("ui-lang", S.lang); applyLang(); });
  $("composer").addEventListener("submit", (e) => { e.preventDefault(); send($("input").value); });
  $("input").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!S.pending) send($("input").value); } });
  $("btn-new").addEventListener("click", newConversation); $("btn-direct").addEventListener("click", runDirect);
  $("tab-chat").addEventListener("click", () => setView("chat")); $("tab-results").addEventListener("click", () => setView("results"));
  $("btn-pick").addEventListener("click", () => { S.mode = "pick"; S.boxCorner = null; updateLocInfo(); }); $("btn-box").addEventListener("click", () => { S.mode = "box"; S.boxCorner = null; updateLocInfo(); });
  $("btn-clear-loc").addEventListener("click", () => { S.point = null; S.bbox = null; S.mode = null; drawSelection(); updateLocInfo(); });
  ["c-lat", "c-lon"].forEach((i) => $(i).addEventListener("change", () => { const la = parseFloat($("c-lat").value), lo = parseFloat($("c-lon").value); if (Number.isFinite(la) && Number.isFinite(lo)) { S.point = {lat: la, lon: lo}; S.bbox = null; drawSelection(); updateLocInfo(); } }));
  $("diag").addEventListener("toggle", (e) => { if (e.target.open) loadDiag(); });
  $("modal-close").addEventListener("click", () => ($("modal").hidden = true)); $("modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("modal").hidden = true; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("modal").hidden = true; });
});
