# ml/ai engineering

core Adaptive RAG pipeline logic.

## architecture

The pipeline uses an **Adaptive RAG** approach with the following loop:

1. **Query**: User asks a question.
2. **Contextualize**: `_generate_standalone_query` uses conversation history to rewrite pronouns/references.
3. **Retrieve**: Hybrid Search (Vector + BM25) fetches top-k (default 10) chunks.
4. **Generate**: Initial answer generation.
5. **Judge**: `JudgeAgent` evaluates the answer for relevance and completeness.
   - If score < 0.7: Suggests refined search tokens -> Re-retrieves -> Re-generates.
6. **Hallucination Check**: `HallucinationDetector` (Singleton) computes an entailment score.

## files

- `rag_pipeline.py`: Main entry point. Implements variables handling, retry loop, and streaming response.
- `retrieval.py`: Hybrid search implementation. Defaults to `top_k=10`.
- `judge.py`: Self-reflection agent. Uses LLM to critique and refine answers.
- `hallucination.py`: Runtime verification using Cross-Encoders (Singleton pattern for performance).
- `vector_store.py`: ChromaDB wrapper.
- `embeddings.py`: Embedding generation (OpenAI/Gemini).

## benchmarks & tuning

- **Tuning**: Found that `top_k=10` is required to capture "Tier 3" eligibility rules (Rank 8).
- **Prompting**: System prompt explicitly handles conditional logic (e.g., "unless", "provided that").

## usage

Run scripts from the `backend` directory using `uv`:

```bash
# 1. Setup & Seeding
uv run python scripts/setup/seed_db.py

# 2. Manual Verification
uv run python tests/manual/manual_rag_test.py

# 3. Tuning & Quality Checks
uv run python scripts/tuning/test_quality.py   # Spot check specific queries
uv run pytest tests/evals/test_rag_quality.py  # Full DeepEval regression suite

# 4. Integration Tests
uv run pytest tests/integration/
```
