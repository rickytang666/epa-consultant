"""
Chunking utilities for merging and splitting text chunks.
"""

import logging
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

from shared.schemas import Chunk

logger = logging.getLogger(__name__)


def merge_chunks(chunks: List[Chunk], chunk_size: int) -> List[Chunk]:
    """
    Merges small chunks that belong to the same header section.
    """
    if not chunks:
        return []
        
    merged = []
    current_chunk = chunks[0]
    
    for next_chunk in chunks[1:]:
        # If next chunk is a table, don't merge it into text!
        if next_chunk.metadata.is_table:
            if current_chunk:  # Flush any accumulated text chunk
                merged.append(current_chunk)
            merged.append(next_chunk) 
            current_chunk = None  # Reset current_chunk as we just added a table
            continue

        if current_chunk is None:  # If previous was a table, start new accumulation
            current_chunk = next_chunk
            continue

        # Check matching headers
        headers_match = (current_chunk.header_path == next_chunk.header_path)
        
        # Check size limit
        combined_len = len(current_chunk.content) + len(next_chunk.content) + 1
        size_ok = combined_len < chunk_size
        
        if headers_match and size_ok:
            # Merge content
            current_chunk = current_chunk.model_copy(
                update={"content": current_chunk.content + "\n" + next_chunk.content}
            )
        else:
            merged.append(current_chunk)
            current_chunk = next_chunk
    
    if current_chunk:
        merged.append(current_chunk)
        
    return merged


def split_chunks(chunks: List[Chunk], chunk_size: int, chunk_overlap: int) -> List[Chunk]:
    """
    Splits chunks that are too large using RecursiveCharacterTextSplitter.
    Preserves chunk_index from previous steps (no renumbering).
    Split chunks get sub-indices in chunk_id (e.g., chunk_001-0, chunk_001-1).
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    
    final_chunks = []
    
    for chunk in chunks:
        # SKIP splitting for tables - keep as-is
        if chunk.metadata.is_table:
            final_chunks.append(chunk)
            continue
            
        # Split large chunks
        if len(chunk.content) > chunk_size:
            split_texts = text_splitter.split_text(chunk.content)
            for i, text in enumerate(split_texts):
                # Use same chunk_index, different chunk_id for splits
                new_chunk = Chunk(
                    document_id=chunk.document_id,
                    chunk_id=f"{chunk.chunk_id}-{i}",
                    content=text,
                    chunk_index=chunk.chunk_index,  # Keep original index
                    location=chunk.location,
                    header_path=chunk.header_path,
                    metadata=chunk.metadata
                )
                final_chunks.append(new_chunk)
        else:
            # Keep chunk as-is
            final_chunks.append(chunk)
    
    return final_chunks
