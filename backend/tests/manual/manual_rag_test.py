import os
import sys
from dotenv import load_dotenv

# add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.rag_pipeline import query_rag_sync

def main():
    load_dotenv()
    
    print("running manual rag test (real api call)...")
    
    # query specific for citations
    query = "What are the eligibility criteria for the PGP?"
    print(f"\nQuestion: {query}")
    print("Answer: ", end="", flush=True)
    
    # stream response
    try:
        chunks = []
        sources_count = 0
        for event in query_rag_sync(query):
            if event["type"] == "content":
                chunks.append(event["delta"])
            elif event["type"] == "sources":
                sources_count = len(event['data'])
        
        if not chunks:
            print("\n[warning] no answer generated. is the database seeded?")
        else:
            # print complete response
            full_response = "".join(chunks)
            print(full_response)
            print(f"\n\n[Sources: {sources_count} chunks retrieved]")
        
        print("\ndone.")
    except Exception as e:
        print(f"\nerror: {e}")

if __name__ == "__main__":
    main()
