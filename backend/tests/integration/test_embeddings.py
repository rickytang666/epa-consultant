import os
import sys
import pytest
from dotenv import load_dotenv

# add backend to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml.embeddings import get_embedding_sync, get_embeddings_batch_sync

# load env vars
load_dotenv()

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY") and not os.getenv("GOOGLE_API_KEY"), reason="missing api key")
def test_get_embedding():
    """test single embedding generation"""
    text = "the epa regulates pesticide use"
    embedding = get_embedding_sync(text)
    
    # check dimension (openai: 1536, gemini: 1536)
    assert len(embedding) in [1536, 1536, 3072]

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY") and not os.getenv("GOOGLE_API_KEY"), reason="missing api key")
def test_get_embeddings_batch():
    """test batch embedding generation"""
    texts = [
        "pesticide registration process",
        "safety guidelines for farmers"
    ]
    embeddings = get_embeddings_batch_sync(texts)
    
    # check count and dimensions
    assert len(embeddings) == 2
    assert len(embeddings[0]) in [1536, 1536, 3072]
    assert len(embeddings[1]) in [1536, 1536, 3072]
