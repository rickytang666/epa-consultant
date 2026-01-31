
import os
import sys
import json
from typing import List, Dict

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.retrieval import retrieve_relevant_chunks, reciprocal_rank_fusion

# 1. Define a "Golden Retrieval" Dataset
# Query -> Expected Substring or Key Phrase that MUST be in the top chunks
GOLDEN_RETRIEVAL_SET = [
    {
        "query": "When does the permit expire?",
        "expected_phrases": ["expires at 11:59 p.m. on October 31, 2026", "administrative continuance"],
        "min_rank": 5 # Must appear in top 5
    },
    {
        "query": "Are discharges to Tier 3 waters eligible?",
        "expected_phrases": ["Tier 3", "Outstanding National Resource Waters", "not eligible"],
        "min_rank": 5
    },
    {
        "query": "What are the four pesticide use patterns?",
        "expected_phrases": ["Mosquito and Other Flying Insect Pest Control", "Forest Canopy Pest Control"],
        "min_rank": 5
    }
]

def evaluate_weights(vector_weight: float, bm25_weight: float):
    print(f"\nEvaluating Weights: Vector={vector_weight} | BM25={bm25_weight}")
    
    hits = 0
    total_mrr = 0.0 # Mean Reciprocal Rank
    
    for case in GOLDEN_RETRIEVAL_SET:
        # Override the weights in the fusion call globally? 
        # Since retrieve_relevant_chunks hardcodes them, we might need to modify it 
        # OR: We just manually call the underlying logic here if we want to loop fast.
        # For this script, let's assume valid integration or mocked weight passing.
        
        # Actually, retrieve_relevant_chunks calls reciprocal_rank_fusion.
        # We need to hack/patch the retrieval function to accept weights 
        # or rewrite the fusion testing locally.
        
        # Let's perform the retrieval manually to control fusion:
        from ml.embeddings import get_embedding
        from ml.vector_store import search_chunks
        from ml.retrieval import _load_bm25_index
        
        # 1. Vector
        embedding = get_embedding(case["query"])
        vec_res = search_chunks(embedding, n_results=20)
        
        # 2. BM25
        bm25, chunks = _load_bm25_index()
        kw_res = []
        if bm25:
            scores = bm25.get_scores(case["query"].lower().split())
            top_n = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:20]
            for i in top_n:
                if scores[i] > 0:
                    c = chunks[i]
                    kw_res.append({"chunk_id": c.get("chunk_id"), "text": c.get("content")})

        # 3. Fusion with dynamic weights
        results = reciprocal_rank_fusion(
            {"vector": vec_res, "bm25": kw_res}, 
            weights={"vector": vector_weight, "bm25": bm25_weight},
            k=60
        )
        
        # Check rank
        found_rank = -1
        for i, r in enumerate(results):
            text = r.get("text", "").lower()
            if any(phrase.lower() in text for phrase in case["expected_phrases"]):
                found_rank = i + 1
                break
        
        if found_rank != -1 and found_rank <= case["min_rank"]:
            hits += 1
            total_mrr += 1.0 / found_rank
            print(f"  ✓ '{case['query'][:30]}...' found at rank {found_rank}")
        else:
            print(f"  ✗ '{case['query'][:30]}...' NOT found in top {case['min_rank']} (Rank: {found_rank if found_rank > 0 else '>20'})")

    score = (hits / len(GOLDEN_RETRIEVAL_SET)) * 100
    mrr = total_mrr / len(GOLDEN_RETRIEVAL_SET)
    print(f"  -> Score: {score:.1f}% | MRR: {mrr:.3f}")
    return score, mrr

if __name__ == "__main__":
    # Grid Search
    grid = [
        (1.0, 1.0),
        (2.0, 1.0),
        (3.0, 1.0),
        (1.0, 2.0),
        (0.5, 1.0) # Keyword heavy
    ]
    
    best_combo = None
    best_mrr = -1
    
    for v, k in grid:
        _, mrr = evaluate_weights(v, k)
        if mrr > best_mrr:
            best_mrr = mrr
            best_combo = (v, k)
            
    print(f"\n🏆 Best Weights: Vector={best_combo[0]}, BM25={best_combo[1]} (MRR: {best_mrr:.3f})")
