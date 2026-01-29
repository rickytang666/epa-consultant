import os
import sys
from dotenv import load_dotenv

# add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ml.rag_pipeline import query_rag

def main():
    load_dotenv()
    
    print("running manual rag test (real api call)...")
    
    # query
    query = "What is the EPA?"
    print(f"\nQuestion: {query}")
    print("Answer: ", end="", flush=True)
    
    # stream response
    try:
        chunks = []
        for event in query_rag(query):
            if event["type"] == "content":
                print(event["delta"], end="", flush=True)
                chunks.append(event["delta"])
            elif event["type"] == "sources":
                print(f"\n[Sources: {len(event['data'])} found]\n")
        
        if not chunks:
            print("\n[warning] no answer generated. is the database seeded?")
            
        print("\n\ndone.")
    except Exception as e:
        print(f"\nerror: {e}")

if __name__ == "__main__":
    main()
