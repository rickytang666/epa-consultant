"""embedding logic using openai text-embedding-3-small"""

from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


def get_embedding(text: str) -> List[float]:
    """
    get embedding vector for text
    
    args:
        text: text to embed
        
    returns:
        embedding vector
    """
    pass


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    get embeddings for multiple texts
    
    args:
        texts: list of texts to embed
        
    returns:
        list of embedding vectors
    """
    pass
