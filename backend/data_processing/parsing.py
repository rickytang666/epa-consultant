"""
Markdown parsing utilities for extracting sections, headers, and tables.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple

from shared.schemas import HeaderNode, ChunkLocation, Chunk, ChunkMetadata

logger = logging.getLogger(__name__)


def split_by_page(markdown_text: str) -> List[str]:
    """Splits markdown by the custom page delimiter."""
    page_split_pattern = r'\n\n\{\d+\}------------------------------------------------\n\n'
    # The split usually results in [empty_preamble, page_1, page_2...]
    return re.split(page_split_pattern, markdown_text)[1:]


def parse_sections(text: str, initial_headers: Optional[Dict[str, str]] = None) -> List[Dict]:
    """Splits markdown text into sections based on headers."""
    lines = text.split('\n')
    chunks = []
    current_content = []
    current_headers = initial_headers.copy() if initial_headers else {}
    
    header_regex = re.compile(r'^(#{1,6})\s+(.*)')
    
    for line in lines:
        match = header_regex.match(line)
        if match:
            # Save previous content
            if current_content:
                chunks.append({
                    "content": "\n".join(current_content).strip(),
                    "metadata": current_headers.copy()
                })
                current_content = []
            
            # Update headers
            level = len(match.group(1))
            name = match.group(2).strip()
            header_key = f"Header {level}"
            
            # Reset lower level headers
            keys_to_remove = [k for k in current_headers if int(k.split()[1]) >= level]
            for k in keys_to_remove:
                del current_headers[k]
                
            current_headers[header_key] = name
        else:
            current_content.append(line)
            
    # Last chunk
    if current_content:
        chunks.append({
            "content": "\n".join(current_content).strip(),
            "metadata": current_headers.copy()
        })
        
    return chunks


def extract_tables(text: str) -> Tuple[str, List[str]]:
    """
    Extracts markdown tables from text.
    Improved detection: requires at least one separator line (|---|---| pattern)
    Returns: (text_with_placeholders, list_of_table_strings)
    """
    lines = text.split('\n')
    new_lines = []
    tables = []
    current_table = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        # Markdown table lines start with |
        if stripped.startswith('|'):
            current_table.append(line)
            # Check if this is a valid table (has separator line)
            if not in_table and len(current_table) >= 2:
                # Look for separator line pattern: |---|---| or | --- | --- |
                for table_line in current_table:
                    if re.match(r'^\|[\s:-]+\|', table_line.strip()):
                        in_table = True
                        break
        else:
            if in_table:
                # Validate table has separator before saving
                has_separator = any(
                    re.match(r'^\|[\s:-]+\|', l.strip()) 
                    for l in current_table
                )
                if has_separator:
                    table_content = "\n".join(current_table)
                    tables.append(table_content)
                    new_lines.append(f"__TABLE_{len(tables)-1}__")
                else:
                    # Not a valid table, add lines back as text
                    new_lines.extend(current_table)
                
                current_table = []
                in_table = False
            
            new_lines.append(line)
    
    # Catch last table
    if in_table and current_table:
        has_separator = any(
            re.match(r'^\|[\s:-]+\|', l.strip()) 
            for l in current_table
        )
        if has_separator:
            tables.append("\n".join(current_table))
            new_lines.append(f"__TABLE_{len(tables)-1}__")
        else:
            new_lines.extend(current_table)
        
    return "\n".join(new_lines), tables


def process_text_pages(pages: List[str], doc_id: str) -> List[Chunk]:
    """Processes each page text, extracting sections, headers, and tables."""
    chunks = []
    global_chunk_index = 1
    global_table_index = 0
    global_header_context = {}

    for i, page_text in enumerate(pages):
        curr_page = i + 1
        
        # 1. Parse sections first (so we know headers)
        sections = parse_sections(page_text, initial_headers=global_header_context)
        
        if sections:
            global_header_context = sections[-1]['metadata'].copy()
        
        for section in sections:
            original_content = section['content']
            if not original_content:
                continue
                
            # 2. Extract tables from THIS section's content
            text_with_placeholders, table_blocks = extract_tables(original_content)
            
            # Setup metadata/headers common to both
            section_metadata = section['metadata']
            header_breadcrumbs = []
            for h_tag, h_name in section_metadata.items():
                header_breadcrumbs.append(HeaderNode(level=h_tag, name=h_name))

            # 3. Create chunks in ORDER based on placeholders
            # Split text by table placeholders to maintain flow
            parts = re.split(r'(__TABLE_\d+__)', text_with_placeholders)
            
            for part in parts:
                if not part.strip():
                    continue
                    
                # Check if it's a table placeholder
                table_match = re.match(r'__TABLE_(\d+)__', part)
                if table_match:
                    table_idx = int(table_match.group(1))
                    if 0 <= table_idx < len(table_blocks):
                        # It's a table
                        global_table_index += 1
                        chunks.append(Chunk(
                            document_id=doc_id,
                            chunk_id=f"chunk_{global_chunk_index:03d}",
                            content=table_blocks[table_idx],
                            chunk_index=global_chunk_index,
                            location=ChunkLocation(page_number=curr_page),
                            header_path=header_breadcrumbs,
                            metadata=ChunkMetadata(
                                is_table=True,
                                table_id=f"table_{global_table_index:03d}",
                                table_title=""
                            )
                        ))
                        global_chunk_index += 1
                else:
                    # It's text
                    chunks.append(Chunk(
                        document_id=doc_id,
                        chunk_id=f"chunk_{global_chunk_index:03d}",
                        content=part.strip(),
                        chunk_index=global_chunk_index,
                        location=ChunkLocation(page_number=curr_page),
                        header_path=header_breadcrumbs,
                        metadata=ChunkMetadata(is_table=False)
                    ))
                    global_chunk_index += 1
    
    return chunks
