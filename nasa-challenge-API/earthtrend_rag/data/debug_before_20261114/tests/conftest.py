import pytest

from app.embeddings.base import HashingEmbedder
from app.models import Document
from app.vector_store.qdrant_store import QdrantStore

SAMPLE_MD = """# Sample Reference

## 1. Intro

Short intro paragraph about NASA data.

## 2. Services

### 2.1 Cards

#### S05 — NASA POWER

- **Auth:** none
- **Units:** T2M in °C, PRECTOTCORR mm/day
- **Limits:** monthly returns YYYY13 annual summary key

```text
curl "https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M"
```

#### S06 — FIRMS

- **Auth:** MAP_KEY required for wildfire hotspots (MODIS, VIIRS)
- **Note:** a hotspot is not burned area

| col | value |
|---|---|
| a | 1 |
| b | 2 |
"""


@pytest.fixture
def embedder():
    return HashingEmbedder(256)


@pytest.fixture
def mem_store(embedder):
    s = QdrantStore(None, embedder.name, embedder.dim)
    yield s
    s.close()


@pytest.fixture
def sample_doc():
    return Document(source_id="test:sample.md", source_file="sample.md", source_type="markdown",
                    title="Sample Reference", text=SAMPLE_MD, collection="earth_knowledge",
                    meta={"source_role": "core_reference"})


@pytest.fixture
def fake_llm():
    class FakeLLM:
        model = "fake-model"

        def __init__(self):
            self.calls = []
            self.reply = "الإجابة من السياق [1]."

        def generate(self, system, user, **kw):
            from app.llm.gemini_client import LLMResult
            self.calls.append((system, user))
            return LLMResult(self.reply, self.model, 10, 5, 0.01)

    return FakeLLM()
