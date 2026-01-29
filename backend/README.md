# epa consultant backend

fastapi backend for querying epa regulatory pdfs using rag.

## setup

### setup using uv

```bash
# install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# or brew on mac
brew install uv

# sync dependencies from pyproject.toml (creates venv automatically)
uv sync

# create .env file
cp .env.example .env
# add your api keys to .env
```

## structure

```
backend/
├── main.py                   # fastapi app entry point
├── data_processing/          # data eng owns this
├── ml/                       # ml/ai eng owns this
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── rag_pipeline.py
│   └── retrieval.py
├── api/                      # full-stack owns this
│   ├── routes.py
│   └── schemas.py
└── data/
    ├── raw/                  # place pdf here
    ├── processed/            # chunks.json, tables.json
    └── chromadb/             # vector db storage
```

## run

```bash
uv run uvicorn main:app --reload

# api will be at http://localhost:8000
# docs at http://localhost:8000/docs
```

## api endpoints

- `GET /` - health check
- `POST /query` - query the rag pipeline (streaming)
- `GET /tables` - get extracted tables

## workflow

1. **data eng**: process pdf → output `chunks.json`
2. **ml/ai**: embed chunks → build rag pipeline → expose `query_rag()` function
3. **full-stack**: build api endpoints → integrate with `query_rag()` → build frontend

## integration points

- **data eng → ml/ai**: `data/processed/chunks.json`
- **ml/ai → full-stack**: `ml.rag_pipeline.query_rag()` function
