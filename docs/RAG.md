# RAG & Knowledge

## Corpus

Files under `knowledge_base/`:

- cancellation_policy.md
- baggage_policy.md
- boarding_rules.md
- faq.md

## Retrieval path

1. **Preferred:** embed query with `sentence-transformers/all-MiniLM-L6-v2` → Supabase `match_knowledge`.
2. **Fallback (always available):** keyword score over markdown files (`app/agents/rag.py`).

## When AI is offline

KnowledgeAgent returns top keyword snippets or a clear “policy KB unavailable” message. Booking and other core flows are unaffected.

## Ingesting new docs

1. Add `.md` / `.txt` under `knowledge_base/`.
2. Optionally embed and upsert into `knowledge_chunks` (script can be extended).
3. Restart backend to reload file corpus cache.
