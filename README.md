<div align="center">

# EPA Pesticide Regulatory Consultant

Process unstructured EPA pesticide regulatory PDFs into queryable, structured data using RAG.

</div>

---

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
