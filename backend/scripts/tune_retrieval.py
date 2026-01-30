import os
import sys
from dotenv import load_dotenv

# add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ml.rag_pipeline import query_rag

def test_top_k():
    load_dotenv()
    
    questions = [
        "What are the eligibility criteria for the PGP?",
        "How does the EPA define an Operator?",
        "What is the permit expiration date?"
    ]
    
    k_values = [1, 3, 5]
    
    for q in questions:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        print(f"{'='*60}")
        
        for k in k_values:
            print(f"\n--- Testing top_k={k} ---")
            
            chunks = []
            sources = []
            
            try:
                for event in query_rag(q, top_k=k):
                    if event["type"] == "content":
                        chunks.append(event["delta"])
                    elif event["type"] == "sources":
                        sources = event["data"]
                
                answer = "".join(chunks).replace("\n", " ").strip()[:200] + "..."
                print(f"Sources Found: {len(sources)}")
                print(f"Answer Preview: {answer}")
                
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    test_top_k()
