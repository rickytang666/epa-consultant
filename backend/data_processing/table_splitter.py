"""
Module for splitting large markdown tables into smaller valid markdown tables.
Ensures headers are preserved for each split to maintain context for RAG.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

def split_markdown_table(table_content: str, max_chars: int = 2000) -> List[str]:
    """
    Splits a massive markdown table into smaller tables, each preserving the header.
    
    Args:
        table_content: The full markdown table string.
        max_chars: Maximum characters per split chunk (soft limit).
        
    Returns:
        List of markdown table strings.
    """
    lines = table_content.strip().split('\n')
    if not lines:
        return []

    # 1. Identify Header
    # Standard MD table usually has:
    # | Header 1 | Header 2 |
    # | --- | --- |
    # | Row 1 | Data |
    
    header_rows = []
    data_rows = []
    separator_index = -1

    # Find the separator line (usually contains mostly dashes and pipes)
    for i, line in enumerate(lines):
        clean_line = line.strip().replace('|', '').replace(' ', '').replace(':', '')
        if clean_line and set(clean_line) <= {'-'}:
            separator_index = i
            break
            
    if separator_index != -1:
        # Include everything up to and including the separator as header
        header_rows = lines[:separator_index + 1]
        data_rows = lines[separator_index + 1:]
    else:
        # Fallback: If no clear separator, assume first 1 line is header (heuristic)
        # This handles malformed tables gracefully by at least splitting content
        header_rows = lines[:1]
        data_rows = lines[1:]

    header_str = "\n".join(header_rows)
    header_len = len(header_str)
    
    # If header itself is massive (unlikely), we warn but proceed
    if header_len > max_chars:
        logger.warning("Table header length (%d) exceeds max_chars (%d)! Splits will be oversized.", header_len, max_chars)

    chunks = []
    current_chunk_rows = []
    current_size = header_len

    for row in data_rows:
        row_len = len(row) + 1 # +1 for newline
        
        # Check if adding this row exceeds limit (ensure we have at least one row per chunk)
        if current_chunk_rows and (current_size + row_len > max_chars):
            # Flush current chunk
            chunk_str = header_str + "\n" + "\n".join(current_chunk_rows)
            chunks.append(chunk_str)
            
            # Reset for next chunk
            current_chunk_rows = [row]
            current_size = header_len + row_len
        else:
            current_chunk_rows.append(row)
            current_size += row_len
            
    # Flush remaining rows
    if current_chunk_rows:
        chunk_str = header_str + "\n" + "\n".join(current_chunk_rows)
        chunks.append(chunk_str)
        
    return chunks
