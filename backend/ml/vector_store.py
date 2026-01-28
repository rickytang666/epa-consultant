"""chromadb operations"""

from typing import List, Dict, Any
import os
import chromadb
from chromadb.config import Settings

# persistence directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CHROMA_DB_DIR = os.path.join(DATA_DIR, "chromadb")

def init_vector_store(collection_name: str = "epa_chunks"):
    """
    initialize chromadb collection
    
    args:
        collection_name: name of the collection
        
    returns:
        chromadb collection object
    """
    # ensure data dir exists
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    
    # init persistent client
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    # get/create collection (cosine similarity)
    collection = client.get_or_create_collection(
        name=collection_name, 
        metadata={"hnsw:space": "cosine"}
    )
    
    return collection


def insert_chunks(chunks: List[Dict[str, Any]], embeddings: List[List[float]], collection_name: str = "epa_chunks"):
    """
    insert chunks and embeddings into chromadb
    
    args:
        chunks: list of chunks with metadata
        embeddings: corresponding embedding vectors
        collection_name: name of the collection
    """
    if not chunks:
        return

    collection = init_vector_store(collection_name)
    
    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    
    # assumes data eng provides clean primitive metadata
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents
    )


def search_chunks(query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    search for similar chunks
    
    args:
        query_embedding: query embedding vector
        top_k: number of results to return
        
    returns:
        list of most similar chunks with metadata
    """
    pass
