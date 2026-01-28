"""retrieval logic"""

from typing import List, Dict, Any
from ml.embeddings import get_embedding
from ml.vector_store import search_chunks

def retrieve_relevant_chunks(query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    retrieve relevant chunks for a query
    
    args:
        query: search query string
        n_results: number of chunks to return
        
    returns:
        list of relevant chunks with metadata
    """
    if not query:
        return []
        
    # generate embedding for query
    embedding = get_embedding(query)
    
    # search vector store
    results = search_chunks(
        query_embedding=embedding,
        n_results=n_results
    )
    
    return results
