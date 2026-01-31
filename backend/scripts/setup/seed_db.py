import os
import sys
import json
import logging
from typing import List, Dict, Any

# add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.embeddings import get_embeddings_batch
from ml.vector_store import insert_chunks
from dotenv import load_dotenv

# setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_chunks(file_path: str) -> tuple[List[Dict[str, Any]], str, Dict[str, str]]:
    """load chunks from json file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    # handle new ProcessedDocument schema (dict with 'chunks' key)
    if isinstance(data, dict) and "chunks" in data:
        logger.info("detected ProcessedDocument schema in chunks.json")
        return (
            data["chunks"], 
            data.get("document_summary", ""), 
            data.get("section_summaries", {})
        )
        
    # handle legacy/tables schema (list of chunks)
    return (data, "", {})

def prepare_chunk_for_store(item: Dict[str, Any], doc_summary: str = "", section_summaries: Dict[str, str] = None) -> Dict[str, Any]:
    """transform raw chunk into format for vector store"""
    
    # 1. basic mapping
    chunk_id = item.get("chunk_id")
    text = item.get("content")
    
    if not chunk_id or not text:
        return None
        
    # 2. flatten metadata
    # chroma only supports primitives (str, int, float, bool)
    metadata = item.get("metadata", {}) or {}
    location = item.get("location", {}) or {}
    
    # merge valid metadata
    clean_metadata = {}
    
    # add top level fields
    if "document_id" in item:
        clean_metadata["document_id"] = str(item["document_id"])
    if "chunk_index" in item:
        clean_metadata["chunk_index"] = int(item["chunk_index"])
        
    # add summaries (if available)
    if doc_summary:
        clean_metadata["document_summary"] = doc_summary
        
    # find most specific section summary
    header_path = item.get("header_path", [])
    if header_path and section_summaries:
        # iterate reversed (deepest header first)
        for h in reversed(header_path):
            h_name = h.get("name", "")
            if h_name and h_name in section_summaries:
                clean_metadata["section_summary"] = section_summaries[h_name]
                break
        
    # add existing metadata fields if primitive
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)) and v is not None:
            clean_metadata[k] = v
            
    # add location fields
    for k, v in location.items():
        if isinstance(v, (str, int, float, bool)) and v is not None:
            clean_metadata[k] = v
            
    # handle header_path (complex object) -> stringify for now
    if header_path:
        # extract just the names as a breadcrumb string
        breadcrumbs = " > ".join([h.get("name", "") for h in header_path])
        clean_metadata["header_path_str"] = breadcrumbs[:1000] # truncate if too long
        
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": clean_metadata
    }

def seed_database():
    load_dotenv()
    
    # path to chunks.json
    # currently assuming backend/scripts is CWD or relative to it
    # file is at backend/data/processed/chunks.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chunks_path = os.path.join(base_dir, "data", "processed", "chunks.json")
    
    if not os.path.exists(chunks_path):
        logger.error(f"chunks.json not found at {chunks_path}")
        return

    logger.info(f"loading chunks from {chunks_path}...")
    raw_items, doc_summary, section_summaries = load_chunks(chunks_path)
    logger.info(f"loaded {len(raw_items)} chunks. doc_summary found: {bool(doc_summary)}")
    
    # process in batches
    BATCH_SIZE = 20
    
    batch_chunks = []
    
    for i, item in enumerate(raw_items):
        processed = prepare_chunk_for_store(item, doc_summary, section_summaries)
        if processed:
            batch_chunks.append(processed)
            
        # process batch
        if len(batch_chunks) >= BATCH_SIZE or (i == len(raw_items) - 1 and batch_chunks):
            try:
                logger.info(f"processing batch {i - len(batch_chunks) + 1} to {i+1}...")
                
                texts = [c["text"] for c in batch_chunks]
                
                # generate embeddings
                # this might take time/money, so logging is important
                embeddings = get_embeddings_batch(texts)
                
                # insert
                insert_chunks(batch_chunks, embeddings)
                
                logger.info(f"batch inserted.")
                
            except Exception as e:
                logger.error(f"failed to process batch: {e}")
                # continue or break? for seeding, maybe better to stop and fix
                # but valid chunks should continue. 
                # let's continue to try to get as much data as possible
                pass
                
            finally:
                batch_chunks = []

    logger.info("seeding complete.")

if __name__ == "__main__":
    seed_database()
