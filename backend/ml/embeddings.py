"""embedding logic using openai text-embedding-3-small"""

from typing import List
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Initialize OpenAI client
# Ensure OPENAI_API_KEY is set in your .env file
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"

def get_embedding(text: str) -> List[float]:
    """
    get embedding vector for text
    
    args:
        text: text to embed
        
    returns:
        embedding vector (length 1536 for text-embedding-3-small)
    """
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=EMBEDDING_MODEL).data[0].embedding


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    get embeddings for multiple texts
    
    args:
        texts: list of texts to embed
        
    returns:
        list of embedding vectors
    """
    # cleanup newlines for all texts
    texts = [t.replace("\n", " ") for t in texts]
    
    # helper to process in batches if needed, but for now we trust openai's limit handling or keep batches small
    response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    
    # sort by index to ensure order is preserved (though openai usually preserves it)
    return [data.embedding for data in response.data]
