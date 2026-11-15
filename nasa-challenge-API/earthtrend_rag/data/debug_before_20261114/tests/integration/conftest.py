import pytest

from app.config import load_gemini_key


@pytest.fixture(scope="session")
def real_service():
    """Real embedding model + persistent production Qdrant index + real Gemini client."""
    from app.rag.service import RagService
    svc = RagService()
    if not svc.health()["index_ready"]:
        svc.ingest()          # builds the index (slow the first time)
    return svc


@pytest.fixture(scope="session")
def need_key():
    """Skips (with the reason) when there is no key OR gemini-3.8-flash is not serving requests right now."""
    if not load_gemini_key():
        pytest.skip("GEMINI_API_KEY not configured")
    from app.llm.gemini_client import GeminiClient, LLMError
    try:
        GeminiClient().generate("Answer in one word.", "Reply OK.", max_output_tokens=16, retries=1)
    except LLMError as e:
        pytest.skip(f"gemini-3.8-flash unavailable during this run ({e}); Gemini-dependent tests NOT executed")


@pytest.fixture(autouse=True)
def _gemini_probe_for_marked(request):
    # tests that call Gemini without the need_key fixture still get the probe
    if request.node.get_closest_marker("integration") and "need_key" not in request.fixturenames and \
            any(n in request.node.name for n in ("real_gemini", "function_calling", "lst_question")):
        request.getfixturevalue("need_key")
