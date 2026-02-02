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
