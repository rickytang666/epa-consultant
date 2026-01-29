<div align="center">

# EPA Pesticide Regulatory Consultant

Process unstructured EPA pesticide regulatory PDFs into queryable, structured data using RAG.

</div>

---

## Quick Run (Localhost)
0. make sure you have python 3.10+ and node 18+ installed (only have to run once)
0.1 in backend, run uv sync and build the venv
0.2 in backend, run scripts in data_processing/README.md and follow instructions to download and process the pdfs
0.3 in backend, run scripts in ml/README.md and follow instructions to build the vector index
0.4 in frontend, run npm install
1. in backend, run uv run uvicorn api.main:app --reload
2. in a second terminal, in frontend, run npm run dev

## Overview

Three-part pipeline to extract, index, and query regulatory document data:

1. **Data Engineering**: Parse PDF, extract tables, chunk document into structured sections
2. **ML/RAG**: Embed chunks, build vector index, retrieve relevant context for queries
3. **Full-Stack**: API and interface for querying document and viewing extracted tables

## How it works

### Data Engineering

- PDF parsing with layout detection
- Table extraction to JSON
- Document chunking
- Handle multi-page tables and inconsistent formatting

### ML Pipeline

- Chunk embedding
- Vector store
- Retrieval: query -> top-k relevant chunks -> LLM with context
- Answer grounding with source citations

### Interface

- REST API for queries and table access
- Simple frontend for Q&A
