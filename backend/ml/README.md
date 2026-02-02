# ml/ai engineering

adaptive rag pipeline with self-correction and hallucination detection.

## architecture

**adaptive rag loop**:

1. **query**: user input.
2. **contextualize**: rewrites query using chat history.
3. **retrieve**: hybrid search (vector + bm25) for top-k chunks.
4. **generate**: initial answer.
5. **judge**: `judgeagent` evaluates quality. if < 0.7, refines search and retries.
6. **hallucination check**: cross-encoder verifies answer logic.

## key files

- **rag_pipeline.py**: main entry point, handles retry loop and streaming.
- **retrieval.py**: hybrid search implementation.
- **judge.py**: self-reflection agent using llm.
- **hallucination.py**: runtime verification (singleton).

## usage

all scripts should be run from `backend/` using `uv`.

### tuning & benchmarks

```bash
# benchmark retrieval performance (requires annotated dataset)
uv run python scripts/tuning/benchmark_retrieval.py

# hyperparameter tuning for retrieval (grid search on k, alpha)
uv run python scripts/tuning/tune_retrieval.py

# verify prompt quality
uv run python scripts/tuning/test_prompt_quality.py
```

### tests

**manual verification**

```bash
# simple manual rag query test
uv run python tests/manual/manual_rag_test.py

# check api citation format
uv run python tests/manual/api_citation_test.py

# visualize chunk tree text
uv run python tests/manual/print_tree.py

# demonstate small chunk splitting logic
uv run python tests/manual/small_chunks_demonstration.py
```

**integration tests**

```bash
# full rag flow integration test
uv run pytest tests/integration/test_rag.py

# vector store integration
uv run pytest tests/integration/test_vector_store.py
```

### acceptance tests (deepeval)

runs `faithfulness` and `answer relevancy` metrics against a golden dataset using deepeval.

```bash
# run acceptance suite
uv run pytest tests/acceptance/test_assignment_criteria.py
```
