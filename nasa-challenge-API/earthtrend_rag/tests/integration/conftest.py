import pytest

from app.config import load_llm_key


@pytest.fixture(scope="session")
def real_service():
    """Real embedding model + persistent production Qdrant index + real Claude client."""
    from app.rag.service import RagService
    svc = RagService()
    if not svc.health()["index_ready"]:
        svc.ingest()          # builds the index (slow the first time)
    return svc


@pytest.fixture(scope="session")
def need_key():
    """Missing credentials block setup; live service failures must FAIL, not skip."""
    if not load_llm_key():
        pytest.skip("ANTHROPIC_API_KEY not configured")
    # Do not spend quota on a duplicate probe or hide live failures behind skips.


@pytest.fixture(autouse=True)
def _llm_probe_for_marked(request):
    # tests that call the model without the need_key fixture still get the probe
    if request.node.get_closest_marker("integration") and "need_key" not in request.fixturenames and \
            any(n in request.node.name for n in ("real_claude", "function_calling", "lst_question")):
        request.getfixturevalue("need_key")
