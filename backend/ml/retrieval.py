"""retrieval logic"""

import os
import json
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from ml.embeddings import get_embedding
from ml.vector_store import search_chunks

# global bm25 index cache
_BM25_INDEX = None
_CHUNKS_CACHE = None


def _load_bm25_index():
    """load chunks and build bm25 index (singleton)"""
    global _BM25_INDEX, _CHUNKS_CACHE

    if _BM25_INDEX is not None:
        return _BM25_INDEX, _CHUNKS_CACHE

    # load chunks
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        chunks_path = os.path.join(base_dir, "data", "processed", "chunks.json")

        with open(chunks_path, "r") as f:
            data = json.load(f)
            # handle schema
            chunks = (
                data["chunks"] if isinstance(data, dict) and "chunks" in data else data
            )
            if not isinstance(chunks, list):
                chunks = []

        # build index
        tokenized_corpus = [c.get("content", "").lower().split() for c in chunks]
        _BM25_INDEX = BM25Okapi(tokenized_corpus)
        _CHUNKS_CACHE = chunks

        return _BM25_INDEX, _CHUNKS_CACHE
    except Exception as e:
        print(f"error loading bm25 index: {e}")
        return None, []


def reciprocal_rank_fusion(
    results: Dict[str, Dict[str, Any]], weights: Dict[str, float] = None, k: int = 60
) -> List[Dict[str, Any]]:
    """
    combine ranked results using Weighted RRF
    score = weight * (1 / (rank + k))
    """
    fused_scores = {}
    if weights is None:
        weights = {key: 1.0 for key in results.keys()}

    for source, result_list in results.items():
        weight = weights.get(source, 1.0)

        for rank, item in enumerate(result_list):
            chunk_id = item.get("chunk_id")
            if not chunk_id:
                continue

            if chunk_id not in fused_scores:
                fused_scores[chunk_id] = {"score": 0, "item": item}

            fused_scores[chunk_id]["score"] += weight * (1 / (rank + k))

    # sort by score desc
    sorted_items = sorted(fused_scores.values(), key=lambda x: x["score"], reverse=True)
    return [x["item"] for x in sorted_items]


async def retrieve_relevant_chunks(
    query: str, n_results: int = 10
) -> List[Dict[str, Any]]:
    """
    retrieve relevant chunks using hybrid search (vector + bm25)

    args:
        query: search query string
        n_results: number of chunks to return

    returns:
        list of relevant chunks with metadata
    """
    if not query:
        return []

    # 1. vector search
    import asyncio

    embedding = await get_embedding(query)
    vector_results = await asyncio.to_thread(
        search_chunks, query_embedding=embedding, n_results=n_results * 2
    )  # fetch more for fusion

    # 2. keyword search (bm25)
    import asyncio

    bm25, chunks_cache = await asyncio.to_thread(_load_bm25_index)
    keyword_results = []

    if bm25:
        tokenized_query = query.lower().split()
        # get top n*2 docs
        doc_scores = await asyncio.to_thread(bm25.get_scores, tokenized_query)
        top_n_indices = sorted(
            range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True
        )[: n_results * 2]

        # normalize to vector store format
        for i in top_n_indices:
            if doc_scores[i] > 0:
                c = chunks_cache[i]

                keyword_results.append(
                    {
                        "chunk_id": c.get("chunk_id"),
                        "text": c.get("content"),
                        "metadata": c.get("metadata", {}) or {},
                    }
                )

                # patch metadata for context (e.g. header path)
                # simpler than querying db; sufficient for hybrid results
                c_meta = c.get("metadata", {}) or {}
                if "header_path" in c:
                    path_str = " > ".join([h["name"] for h in c["header_path"]])
                    c_meta["header_path_str"] = path_str
                keyword_results[-1]["metadata"] = c_meta

    # 3. fusion
    # TODO: tune weights
    fused_results = reciprocal_rank_fusion(
        {"vector": vector_results, "bm25": keyword_results},
        weights={"vector": 1.0, "bm25": 1.0},
    )

    # 4. Repair formatting (heuristic for broken tables)
    final_results = fused_results[:n_results]
    for res in final_results:
        if "text" in res and res["text"]:
            res["text"] = _repair_table_formatting(res["text"])

    return final_results


def _repair_table_formatting(text: str) -> str:
    """
    heuristic to fix common markdown table issues (flattened rows)
    e.g. '| header ||---|' -> '| header |\n|---|'
    """
    import re

    # 1. safe fix: header/separator join (always fix)
    # matches '|' then '|---' or '|:'
    text = re.sub(r"(\|\s*)(\|[-:]+)", r"\1\n\2", text)

    # 2. aggressive fix: row/row join
    # only apply if text looks like a flattened table (long but few newlines)
    if len(text) > 200 and text.count("\n") < 3:
        # replace || with |\n|
        # assumes valid empty cells | | are spaced, or rare in this specific flattened context
        text = text.replace("||", "|\n|")

    return text
