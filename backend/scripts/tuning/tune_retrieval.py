import os
import sys
from dotenv import load_dotenv

# add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.rag_pipeline import query_rag_sync

def test_top_k():
    load_dotenv()
    
    questions = [
        "When does this permit expire?",
        "Are discharges to Tier 3 waters eligible for coverage?"
    ]
    
    k_values = [3, 5, 10]
    
    for q in questions:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        print(f"{'='*60}")
        
        for k in k_values:
            print(f"\n--- Testing top_k={k} ---")
            
            chunks = []
            sources = []
            
            try:
                for event in query_rag_sync(q, top_k=k):
                    if event["type"] == "content":
                        # suppress generation output for cleaner debugging
                        pass 
                    elif event["type"] == "sources":
                        sources = event["data"]
                
                print(f"Sources Found: {len(sources)}")
                for i, s in enumerate(sources):
                    print(f"  [{i+1}] {s.get('text', '')[:150]}...")
                    if 'expire' in s.get('text', '').lower() or 'effective' in s.get('text', '').lower():
                        print(f"      *** POTENTIAL HIT ***")
                
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    test_top_k()
