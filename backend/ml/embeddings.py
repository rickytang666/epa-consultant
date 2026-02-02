"""embedding logic using unified LLM provider"""

from typing import List
import logging
from shared.llm_provider import LLMProvider

# Lazy initialization to avoid import-time env var requirements
_llm_instance = None

def _get_llm():
    """Lazy-load LLM provider on first use."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMProvider()
    return _llm_instance

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_embedding(text: str) -> List[float]:
    """
    get embedding vector for text using unified provider
    
    args:
        text: text to embed
        
    returns:
        embedding vector
    """
    # cleanup newlines
    text = text.replace("\n", " ")
    
    try:
        return await _get_llm().embed(text, use_case="embeddings")
    except Exception as e:
        raise RuntimeError(f"Embedding failed: {e}")


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    get embeddings for multiple texts using unified provider
    
    args:
        texts: list of texts to embed
        
    returns:
        list of embedding vectors
    """
    # cleanup newlines for all texts
    texts = [t.replace("\n", " ") for t in texts]
    
    try:
        return await _get_llm().embed(texts, use_case="embeddings")
    except Exception as e:
        raise RuntimeError(f"Batch embedding failed: {e}")


# Sync wrappers for backward compatibility
def get_embedding_sync(text: str) -> List[float]:
    """Synchronous wrapper for get_embedding. Use async version when possible."""
    import asyncio
    import threading
    
    result = None
    exception = None
    
    def run_in_thread():
        nonlocal result, exception
        try:
            result = asyncio.run(get_embedding(text))
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    
    if exception:
        raise exception
    return result


def get_embeddings_batch_sync(texts: List[str]) -> List[List[float]]:
    """Synchronous wrapper for get_embeddings_batch. Use async version when possible."""
    import asyncio
    import threading
    
    result = None
    exception = None
    
    def run_in_thread():
        nonlocal result, exception
        try:
            result = asyncio.run(get_embeddings_batch(texts))
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    
    if exception:
        raise exception
    return result

