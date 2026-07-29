"""RAG over knowledge_base – Chroma + sentence-transformers, keyword fallback."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from app.config import get_settings

KB_DIR = Path(__file__).resolve().parents[3] / "knowledge_base"
CHROMA_DIR = Path(__file__).resolve().parents[2] / ".chroma_busmate"

_CORPUS: List[Tuple[str, str]] = []
_chroma = None
_embedder = None
_collection = None


def _load_corpus() -> List[Tuple[str, str]]:
    global _CORPUS
    if _CORPUS:
        return _CORPUS
    if not KB_DIR.exists():
        return []
    for path in sorted(KB_DIR.glob("**/*")):
        if path.suffix.lower() in {".md", ".txt"}:
            try:
                text = path.read_text(encoding="utf-8")
                _CORPUS.append((path.name, text))
            except OSError:
                continue
    return _CORPUS


def keyword_retrieve(query: str, top_k: int = 4) -> List[str]:
    corpus = _load_corpus()
    q_terms = set(query.lower().split())
    scored: List[Tuple[int, str]] = []
    for name, text in corpus:
        t_lower = text.lower()
        score = sum(1 for t in q_terms if t in t_lower)
        if score:
            scored.append((score, f"[{name}]\n{text[:600].strip()}"))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:top_k]]


def _init_chroma() -> bool:
    """Lazy-init Chroma collection. Returns False if deps unavailable."""
    global _chroma, _embedder, _collection
    if _collection is not None:
        return True
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return False

    settings = get_settings()
    try:
        _embedder = SentenceTransformer(settings.embedding_model)
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _chroma.get_or_create_collection(
            name="busmate_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
        if _collection.count() == 0:
            corpus = _load_corpus()
            if not corpus:
                return True
            ids, docs, metas = [], [], []
            for name, text in corpus:
                chunks = [text[j : j + 500] for j in range(0, len(text), 500)]
                for k, chunk in enumerate(chunks):
                    ids.append(f"{name}-{k}")
                    docs.append(chunk)
                    metas.append({"source": name})
            embeddings = _embedder.encode(docs, show_progress_bar=False).tolist()
            _collection.add(
                ids=ids, documents=docs, metadatas=metas, embeddings=embeddings
            )
        return True
    except Exception:
        _collection = None
        return False


def vector_retrieve(query: str, top_k: int = 4) -> Optional[List[str]]:
    if not _init_chroma() or _collection is None or _embedder is None:
        return None
    try:
        q_emb = _embedder.encode([query], show_progress_bar=False).tolist()
        res = _collection.query(query_embeddings=q_emb, n_results=top_k)
        docs = res.get("documents") or [[]]
        metas = res.get("metadatas") or [[]]
        out: List[str] = []
        for doc, meta in zip(docs[0], metas[0]):
            src = (meta or {}).get("source", "doc")
            out.append(f"[{src}]\n{doc}")
        return out
    except Exception:
        return None


async def retrieve(query: str, top_k: int | None = None) -> List[str]:
    settings = get_settings()
    k = top_k or settings.rag_top_k
    vec = vector_retrieve(query, k)
    if vec:
        return vec
    return keyword_retrieve(query, k)
