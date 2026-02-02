<div align="center">

# EPA Pesticide Regulatory Consultant

An intelligent RAG system for querying unstructured EPA pesticide regulatory PDFs.

</div>

---

## Introduction

A RAG pipeline that transforms unstructured EPA regulatory PDFs into structured, queryable data. It uses hybrid search (Vector + BM25), a self-correcting "Judge" agent, and runtime hallucination detection to ensure high-accuracy answers with cited evidence.

## Tech Stack

- **Backend**: Python, FastAPI, LangChain, ChromaDB, LLMs (OpenAI/Gemini/OpenRouter), DeepEval, DataLab/PyMuPDF4LLM, Pydantic, Pytest, uv
- **Frontend**: TypeScript, React, Vite, Tailwind CSS, Playwright

## Usage

### Prerequisites

- Python 3.10+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) (for backend dependency management)

### Setup & Run

**Backend**

```bash
cd backend

# Install dependencies and create virtualenv
uv sync

# Setup environment variables
cp .env.example .env

# Data Preparation (Required for first run)
# 1. Place your PDFs in backend/data/raw/
# 2. Run the ingestion pipeline (Extract -> Parse -> Chunk)
uv run python scripts/pipeline/run_pipeline.py
# 3. Seed the Vector Database
uv run python scripts/setup/seed_db.py

# Run API server
uv run uvicorn main:app --reload
# API available at http://localhost:8000
```

**Frontend**

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
# App available at http://localhost:5173
```

> **Note**: For detailed data processing and ML scripts, see `backend/data_processing/README.md` and `backend/ml/README.md`.

## How It Works

### 1. Data Ingestion (Data Engineering)

- **Extraction**: Uses DataLab API to convert PDFs into Markdown, preserving layout and tables.
- **Parsing**: Splits documents by page and identifies hierarchical sections.
- **Correction**: Uses LLM to fix broken header hierarchies (e.g., detecting that "1.0" is a sub-header of "Section 1") based on numbering patterns.
- **Chunking**: Merges small sections and improved splitting of large sections to maintain context window efficiency.

### 2. Adaptive RAG (ML)

- **Hybrid Search**: Combines Dense Vector Retrieval (semantic search) with BM25 (keyword search) to capture both conceptual matches and specific regulatory codes.
- **Self-Correction Loop**: A "Judge Agent" evaluates generated answers for relevance. If confidence is low (< 0.7), it rewrites the search query and retries.
- **Hallucination Detection**: A dedicated Cross-Encoder model verifies that the generated answer is strictly entailed by the retrieved context before returning it to the user.
- **Evaluation**: Uses DeepEval to run acceptance tests against a golden dataset, measuring faithfulness and answer relevancy to ensure rigorous quality standards.

### 3. User Interface (Full-Stack)

- **Q&A**: Interactive chat interface for querying documents.
- **Citations**: Answers include citations linking back to specific source chunks.
- **Tables**: Dedicated view for extracted regulatory tables.

## Team

- Justin Jonany
- Ricky Tang
- Richard Zhu
