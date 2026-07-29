# Dependency Version Rationale

Target: **Python 3.10.11**, Windows 11, `pip install -r requirements.txt` with **no LiteLLM / no Rust toolchain**.

## Root conflict (why the old pins failed)

| Package (old) | Required `openai` |
|---------------|-------------------|
| `langchain-openai==0.3.0` | **1.x** |
| `crewai==1.15.5` | **2.x** |

Those two cannot install together. Older CrewAI also pulled **LiteLLM**, which often tries to compile native extensions (Rust) on Windows.

## Chosen stack (aligned on OpenAI SDK 2.x)

| Package | Constraint | Why |
|---------|------------|-----|
| **openai** | `>=2.30.0,<3` | Shared by CrewAI native provider and LangChain 1.x |
| **crewai[openai]** | `>=1.14.0,<2` | Official **native OpenAI extra** — **no LiteLLM**, no Rust build |
| **langchain** / **langchain-core** | `>=1.0,<2` | LangChain 1.x requires openai 2.x via langchain-openai 1.x |
| **langchain-openai** | `>=1.0,<2` | Pins `openai>=2.45` in current releases; matches CrewAI |
| **langchain-community** | `>=0.3.20,<0.5` | Community loaders/utilities; stays compatible with core 1.x |
| **langgraph** | `>=1.0,<2` | StateGraph routing used in `app/agents/graph.py` |
| **chromadb** | `>=0.5.23,<1.1` | Local vector store for RAG (no cloud key required) |
| **sentence-transformers** | `>=3,<4` | Local embeddings for Chroma (`all-MiniLM-L6-v2`) |
| **numpy** | `>=1.26,<2.1` | Avoids numpy 2.x breakages with some ST wheels on Win |

**Not installed:** `litellm`, `crewai[litellm]`, old `langchain-openai 0.3.x`, old `crewai 0.86`.

## How OpenRouter is wired

OpenRouter is OpenAI-compatible:

- LangChain: `ChatOpenAI(base_url=OPENROUTER_BASE_URL, api_key=...)`
- CrewAI: `LLM(model=..., api_key=..., base_url=...)`
- Raw: `openai.OpenAI(base_url=..., api_key=...)`

No LiteLLM proxy required.

## Runtime without API keys

If `OPENROUTER_API_KEY` is empty:

- Intent gate + keyword RAG + demo booking still work
- CrewAI / LLM nodes return friendly fallbacks
- FastAPI starts normally

## Install

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```

If `sentence-transformers` or `chromadb` fail on a minimal machine, core API still runs; RAG falls back to keyword search.
