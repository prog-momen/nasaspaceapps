"""Evidence relevance checks for documentation answers.

A retrieved passage becomes answer evidence only when it is individually relevant to THIS question:
  * dense similarity above the pipeline threshold (embedding match; works across Arabic/English), and
  * when question and passage share a script, enough of the question's content terms must actually occur in the passage text/metadata
    (lexical support). Cross-script pairs rely on a stricter dense margin instead, because lexical overlap is impossible there.
This is deliberately a precision gate: unrelated pages that merely sit near the question in embedding space are dropped, and when nothing
survives the answer is 'Insufficient resources...' rather than a padded reply.
"""
from __future__ import annotations

import re

_STOP_EN = set("""a an the of in on at to for from by with and or is are was were be been what which who how why when where does do did can could should would will
about between into than then that this these those it its as if not no yes there their them they you your i we our us me my tell show give list explain describe
nasa data dataset api available use used using mean means meaning provide provides parameter need needs know want get make much many""".split())
_STOP_AR = set("ما ماذا هو هي هل في من الى إلى على عن مع او أو ان أن التي الذي هذا هذه ذلك كيف لماذا متى اين أين كم يمكن يمكنني اشرح اذكر اعطني أعطني".split())
_AR = re.compile(r"[؀-ۿ]")
_TOK = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}|[؀-ۿ]{3,}|\d{2,}")
_IDENT = re.compile(r"(?:[A-Za-z]+[-_]?\d[A-Za-z0-9]*|\d{3,})")


def _stem(t: str) -> str:
    t = t.lower()
    if _AR.search(t):
        t = re.sub(r"^(?:ال|وال|بال|لل)", "", t)
        return t[:5]
    return t[:6]


def content_terms(text: str) -> set[str]:
    out = set()
    for tok in _TOK.findall(text or ""):
        low = tok.lower()
        if low in _STOP_EN or low in _STOP_AR:
            continue
        out.add(_stem(tok))
    return out


def same_script(a: str, b: str) -> bool:
    return bool(_AR.search(a)) == bool(_AR.search(b))


def lexical_coverage(question: str, passage: str) -> float:
    q = content_terms(question)
    if not q:
        return 1.0
    toks = _TOK.findall(passage or "")
    toks += [x for t in toks for x in t.split("_") if len(x) >= 3]            # MAP_KEY also matches 'key'
    p = {_stem(t) for t in toks}
    hit = sum(1 for t in q if t in p or any(x.startswith(t) for x in p))
    return hit / len(q)


MIN_COVERAGE = 0.34       # same-script: at least a third of the question's content terms must occur in the passage
CROSS_SCRIPT_MARGIN = 0.02


def identifiers_present(question: str, passage: str) -> bool:
    """Code-like tokens in the question (MOD11, XYZ-9000, 2040, T2M) must occur verbatim in the passage: a passage that lacks them cannot support the claim."""
    low = (passage or "").lower()
    return all(tok.lower() in low for tok in _IDENT.findall(question or ""))


def supports(question: str, text: str, meta_text: str, dense: float | None, threshold: float) -> bool:
    if dense is None or dense < threshold:
        return False
    blob = f"{meta_text} {text}"
    if not identifiers_present(question, blob):
        return False
    if same_script(question, blob[:600]):
        return lexical_coverage(question, blob) >= MIN_COVERAGE
    # cross-script (e.g. English question, Arabic reference): stricter dense margin AND at least one shared term (product/identifier names are Latin in both)
    return dense >= threshold + CROSS_SCRIPT_MARGIN and lexical_coverage(question, blob) > 0


_POWER_PARAMS = [(re.compile(r"precip|rain|هطول|أمطار|امطار|مطر", re.I), "PRECTOTCORR"), (re.compile(r"temperature|حرارة", re.I), "T2M"),
                 (re.compile(r"humidity|رطوبة", re.I), "RH2M"), (re.compile(r"\bwind|رياح", re.I), "WS2M")]


def expand_query(question: str) -> str:
    """Retrieval-only expansion: a question about a NASA POWER variable also searches for the official parameter code that the
    reference documents use (e.g. precipitation -> PRECTOTCORR). The answer is still judged against the ORIGINAL question."""
    if not re.search(r"\bpower\b|باور", question, re.I):
        return question
    extra = [code for rx, code in _POWER_PARAMS if rx.search(question) and code.lower() not in question.lower()]
    return question + (" " + " ".join(extra) if extra else "")


DIRECT_MIN_COVERAGE = 0.6


def directly_answers(question: str, passage: str) -> bool:
    """Stricter than `supports`: used before SHOWING a passage to the user without a model to synthesise an answer.
    Most of the question's content terms (and every identifier) must occur in the passage itself."""
    return identifiers_present(question, passage) and lexical_coverage(question, passage) >= DIRECT_MIN_COVERAGE
