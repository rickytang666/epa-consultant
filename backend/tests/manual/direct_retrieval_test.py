import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml.retrieval import retrieve_relevant_chunks

async def main():
    load_dotenv()
    query = "What is the Pesticide General Permit (PGP)?"
    print(f"Testing direct retrieval for query: '{query}'")
    
    try:
        results = await retrieve_relevant_chunks(query, n_results=3)
        
        print(f"\nFound {len(results)} results:")
        for i, res in enumerate(results):
            print(f"\n--- Result {i+1} (ID: {res['chunk_id']}) ---")
            print(f"Text Preview: {res['text'][:200]}...")
            print(f"Metadata: {res['metadata']}")
            
    except Exception as e:
        print(f"Error during retrieval: {e}")

if __name__ == "__main__":
    asyncio.run(main())
