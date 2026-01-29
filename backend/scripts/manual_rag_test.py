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
        for chunk in query_rag(query):
            print(chunk, end="", flush=True)
            chunks.append(chunk)
        
        if not chunks:
            print("\n[warning] no answer generated. is the database seeded?")
            
        print("\n\ndone.")
    except Exception as e:
        print(f"\nerror: {e}")

if __name__ == "__main__":
    main()
