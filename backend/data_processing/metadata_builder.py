"""add metadata to chunks"""

from typing import List, Dict, Any


def add_metadata(chunks: List[Dict[str, Any]], doc_source: str) -> List[Dict[str, Any]]:
    """
    add metadata to each chunk
    
    args:
        chunks: list of chunks from chunker
        doc_source: source document name
        
    returns:
        chunks with complete metadata (page, chunk_id, headings, etc.)
    """
    pass


def build_chunk_schema(chunk_id: str, text: str, page: int, doc_source: str, 
                       is_table: bool = False, heading1: str = None, 
                       heading2: str = None, heading3: str = None) -> Dict[str, Any]:
    """
    build a single chunk with proper schema
    
    returns:
        {
            "chunk_id": "chunk_001",
            "text": "...",
            "metadata": {
                "page": 42,
                "doc_source": "2026-pgp.pdf",
                "is_table": false,
                "heading1": "...",
                "heading2": "...",
                "heading3": "..."
            }
        }
    """
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": {
            "page": page,
            "doc_source": doc_source,
            "is_table": is_table,
            "heading1": heading1,
            "heading2": heading2,
            "heading3": heading3
        }
    }
