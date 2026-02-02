# epa consultant backend

backend for querying epa regulatory pdfs using rag.

## setup

```bash
# install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# sync dependencies
uv sync

# setup env
cp .env.example .env
```

## run

```bash
uv run uvicorn main:app --reload
# api at http://localhost:8000
# docs at http://localhost:8000/docs
```

## api

- `GET /` - health check
- `POST /query` - rag query
- `GET /tables` - extracted tables

## testing

running acceptance tests (deepeval):

```bash
uv run pytest tests/acceptance/test_assignment_criteria.py
```

### quick response check

to see how the agent answers the test questions without running the full evaluation metrics:

```bash
uv run python scripts/test_responses.py
```
