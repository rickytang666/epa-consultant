# ml/ai engineering

core rag pipeline logic.

## files

- `embeddings.py`: handles embedding generation. supports openai (`text-embedding-3-small`) and google gemini (`embedding-001`). auto-fallback.
- `vector_store.py`: chromadb wrapper. handles persistence, collection management, insertion, and semantic search.
- `retrieval.py`: connects embeddings to vector store. takes a query, embeds it, and retrieves top-k chunks.
- `rag_pipeline.py`: main entry point. `query_rag(query)` generates streaming answers using retrieved context. uses openrouter (`gpt-oss-120b`) with gemini fallback.

## scripts

- `backend/scripts/seed_db.py`: loads `chunks.json`, generates embeddings, and populates chromadb. run this once.
- `backend/scripts/manual_rag_test.py`: simple script to query the pipeline and verify end-to-end functionality.
- `backend/tests/test_rag_quality.py`: factual QA test suite. checks answers against 5 known questions.

## usage

run scripts from the `backend` directory:

```bash
# 1. seed the database (required first time ONLY)
uv run python scripts/seed_db.py

# 2. run manual verification
uv run python scripts/manual_rag_test.py

# 3. run quality tests
uv run pytest tests/test_rag_quality.py -s
```
