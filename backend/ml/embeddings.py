"""embedding logic using openai text-embedding-3-small or google gemini"""

from typing import List
import os
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# client initialization
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

google_client = None
if GOOGLE_API_KEY:
    google_client = genai.Client(api_key=GOOGLE_API_KEY)

# models
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_google_embedding(text: str) -> List[float]:
    if not google_client:
        raise ValueError("google_client not initialized")
        
    result = google_client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    # result.embeddings is a list of embedding objects
    return result.embeddings[0].values

def _get_openai_embedding(text: str) -> List[float]:
    if not openai_client:
        raise ValueError("openai_client not initialized")
        
    return openai_client.embeddings.create(input=[text], model=OPENAI_EMBEDDING_MODEL).data[0].embedding

def get_embedding(text: str) -> List[float]:
    """
    get embedding vector for text
    tries openai first, fails over to google gemini
    
    args:
        text: text to embed
        
    returns:
        embedding vector
    """
    # cleanup newlines
    text = text.replace("\n", " ")
    
    # try openai
    if openai_client:
        try:
            return _get_openai_embedding(text)
        except Exception as e:
            logger.warning(f"openai embedding failed: {e}. falling back to google gemini.")
    
    # fallback to google
    if google_client:
        try:
            logger.info("using google gemini embeddings (dim: 768)")
            return _get_google_embedding(text)
        except Exception as e:
            raise RuntimeError(f"google embedding also failed: {e}")
            
    raise ValueError("no working api key found for openai or google.")


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    get embeddings for multiple texts
    tries openai first, fails over to google gemini
    
    args:
        texts: list of texts to embed
        
    returns:
        list of embedding vectors
    """
    # cleanup newlines for all texts
    texts = [t.replace("\n", " ") for t in texts]
    
    # try openai
    if openai_client:
        try:
            response = openai_client.embeddings.create(input=texts, model=OPENAI_EMBEDDING_MODEL)
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.warning(f"openai batch embedding failed: {e}. falling back to google gemini.")

    # fallback to google
    if google_client:
        try:
            logger.info("using google gemini batch embeddings (dim: 768)")
            result = google_client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
             raise RuntimeError(f"google batch embedding also failed: {e}")

    raise ValueError("no working api key found for openai or google.")
