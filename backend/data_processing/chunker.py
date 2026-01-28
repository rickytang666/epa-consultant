"""chunk text by sections with overlap"""

from typing import List, Dict, Any


def chunk_text(parsed_content: Dict[str, Any], chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """
    chunk text into sections with overlap
    
    args:
        parsed_content: output from pdf_parser
        chunk_size: target chunk size in characters
        overlap: overlap between chunks in characters
        
    returns:
        list of chunks with text and metadata
    """
    pass
