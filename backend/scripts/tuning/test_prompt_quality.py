"""
test quality of prompt engineering
"""
import os
import sys
from dotenv import load_dotenv

# add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.rag_pipeline import query_rag_sync

def test_quality():
    load_dotenv()
    
    query = "Are discharges to Tier 3 waters eligible for coverage?"
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}\n")
    
    try:
        full_answer = ""
        for event in query_rag_sync(query, top_k=10):
            if event["type"] == "content":
                full_answer += event["delta"]
            elif event["type"] == "sources":
                print(f"[Sources Found: {len(event['data'])}]")
        
        print("\n" + "="*20 + " ANSWER " + "="*20)
        print(full_answer)
        print("="*48 + "\n")
        
        print("\n\n" + "="*60)
        
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    test_quality()
