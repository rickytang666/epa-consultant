# data processing module

pipeline for processing pdfs into rag-ready chunks with hierarchical logic.

## pipeline flow

1. **extract**: pdf -> markdown (via datalab api).
2. **ingest**: split pages -> parse headers -> correct headers (llm) -> merge/split chunks.
3. **enrich**: generate hierarchical summaries (section/document).

## modules

### pdf_extractor.py

- sync/async extraction via datalab api.
- outputs markdown + metadata to `data/extracted/`.

### ingest.py

- main orchestrator.
- coordinates parsing, header correction, chunking, and summarization.

### parsing.py

- splits by page.
- extracts sections and tables.

### header_correction.py

- **problem**: pdfs often have broken header levels (e.g. "1.0" detected as h2).
- **solution**: extracts headers, sends to llm to fix hierarchy based on numbering (1.0 -> 1.1), applies fixes to chunks.

### chunking.py

- `merge_chunks()`: combines small chunks under same header.
- `split_chunks()`: splits large chunks (recursive character splitter) preserving header context.

### summarization.py

- generates bottom-up summaries (section -> document).
- uses `section_summary.jinja2` and `document_summary.jinja2`.

### extract_tables.py

- rebuilds `tables.json` from extraction.
- handles multi-page merging (e.g. Regions 4/10).
- deduplicates sequential table fragments.
- cleans HTML tags and fixes headers.

## usage

all scripts should be run from `backend/` using `uv`.

### pipeline scripts

```bash
# extract pdfs (files in data/raw -> data/extracted)
uv run python scripts/pipeline/run_pdf_extraction.py

# parse extraction (json in data/extracted -> data/processed)
# Use --fix-headers to enable llm header correction
uv run python scripts/pipeline/run_parsing.py "filename.json" --fix-headers

# run full pipeline (extract + parse)
uv run python scripts/pipeline/run_pipeline.py

# run table extraction (required for frontend Table Explorer)
uv run python scripts/pipeline/extract_tables.py
```

### setup

```bash
# seed database with processed data
uv run python scripts/setup/seed_db.py
```

### benchmarks

```bash
# benchmark summarization costs/speed
uv run python scripts/benchmarks/benchmark_summarization.py

# benchmark cost savings from child chunk deduplication
uv run python scripts/benchmarks/benchmark_cost_savings.py

# benchmark adaptive chunk sampling
uv run python scripts/benchmarks/benchmark_adaptive_sampling.py
```
