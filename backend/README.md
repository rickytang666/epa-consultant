# epa consultant backend

fastapi backend for querying epa regulatory pdfs using rag.

## setup

```bash
# create virtual environment
python -m venv venv
source venv/bin/activate  # on windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# create .env file
cp .env.example .env
# add your api keys to .env
```

## structure

```
backend/
├── main.py                   # fastapi app entry point
├── data_processing/          # data eng owns this
│   ├── pdf_parser.py
│   ├── chunker.py
│   ├── table_extractor.py
│   └── metadata_builder.py
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
# development
python main.py

# or with uvicorn
uvicorn main:app --reload

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
