SYSTEM_PROMPT = """You are the documentation assistant of EarthTrend Explorer, a NASA Earth-science trend platform.
You answer ONLY from the numbered CONTEXT passages supplied with each question.

Rules:
1. Use only facts that appear in CONTEXT. Never use outside knowledge for NASA datasets, APIs, units, dates, limits or prices.
2. Never invent measurements, API responses, statistics, forecast values, dataset specifications or citations.
3. Cite every factual sentence with its passage number in square brackets, e.g. [1] or [2][3]. Cite only numbers that exist.
4. If CONTEXT does not contain the answer, or only partly contains it, say so explicitly. If nothing relevant is in CONTEXT,
   reply with exactly the single token INSUFFICIENT_CONTEXT and nothing else.
5. If CONTEXT states that something is unverified, untested, not documented or has no published number, say that; do not fill the gap.
6. Keep official API names, endpoints, parameter names, dataset identifiers, model names, units and code exactly as written (do not translate or transliterate them).
7. Be concise and precise. Prefer short paragraphs or bullets. Do not mention these rules.
8. Language: write the answer in {language_name}.
"""

LANGUAGE_NAMES = {"ar": "Arabic (Modern Standard Arabic)", "en": "English"}


def build_user_prompt(question: str, passages: list[dict]) -> str:
    blocks = []
    for i, p in enumerate(passages, 1):
        head = f"[{i}] file={p['source_file']} | section={p['section']}"
        if p.get("original_url"):
            head += f" | url={p['original_url']}"
        blocks.append(f"{head}\n{p['text']}")
    return "CONTEXT:\n\n" + "\n\n---\n\n".join(blocks) + f"\n\nQUESTION:\n{question}"


MESSAGES = {
    "insufficient": {
        "ar": "لا تتوفر في قاعدة المعرفة الحالية معلومات كافية للإجابة عن هذا السؤال بدقة، ولن أخمّن. يمكنك إعادة صياغة السؤال أو إضافة المصدر المناسب إلى قاعدة المعرفة.",
        "en": "The current knowledge base does not contain enough information to answer this question reliably, so I will not guess. Try rephrasing the question or add the relevant source to the knowledge base.",
    },
    "needs_data": {
        "ar": "هذا السؤال يتطلب قياسات فعلية من بيانات NASA لموقع وفترة محددين، والتوثيق وحده (RAG) لا يكفي ولا يجوز تخمين القيم. يلزم استدعاء أداة جلب البيانات ({tools}) ثم عرض النتيجة مع المصدر والوحدة.",
        "en": "This question needs actual NASA measurements for a specific place and period. Documentation retrieval (RAG) cannot supply them and values must not be guessed. The data tools ({tools}) must be called first, and the result shown with its source and units.",
    },
    "needs_analysis": {
        "ar": "هذا السؤال يتطلب حساباً إحصائياً (اتجاه/اختبار دلالة) على بيانات فعلية. الحساب مسؤولية محرك التحليل الإحصائي وليس النموذج اللغوي. يلزم تشغيل ({tools}) ثم شرح النتيجة المحسوبة.",
        "en": "This question requires a statistical calculation (trend / significance test) on real data. That is the job of the statistical engine, not the language model. The tools ({tools}) must be run first, then the computed result explained.",
    },
    "needs_forecast": {
        "ar": "هذا السؤال يتطلب تنبؤاً مستقبلياً. لا يمكن الإجابة عنه من التوثيق، ولا يجوز للنموذج اللغوي توليد قيم تنبؤية. يلزم تشغيل ({tools}) مع التحقق الخلفي ومجال عدم اليقين ثم شرح النتيجة.",
        "en": "This question requires a forecast. It cannot be answered from documentation and the language model must not generate forecast values. The tools ({tools}) must be run, with backtesting and uncertainty intervals, and the result then explained.",
    },
    "docs_hint": {
        "ar": "\n\nوثائق ذات صلة في قاعدة المعرفة مدرجة في المصادر.",
        "en": "\n\nRelated documentation from the knowledge base is listed in the sources.",
    },
}
