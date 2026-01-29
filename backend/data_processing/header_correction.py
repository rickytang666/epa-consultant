"""
LLM-based header hierarchy correction.
"""

import re
import logging
from typing import List, Tuple, Dict, Optional

from .models import HeaderAnalysis
from .prompts import get_header_correction_template
from .llm_client import LLMClient
from shared.schemas import Chunk, HeaderNode

logger = logging.getLogger(__name__)


def extract_unique_headers(chunks: List[Chunk]) -> List[tuple]:
    """Extract unique headers from chunks."""
    seen = set()
    unique = []
    for chunk in chunks:
        for header in (chunk.header_path or []):
            key = (header.level, header.name)
            if key not in seen:
                seen.add(key)
                unique.append(key)
    return unique


def correct_headers(chunks: List[Chunk], llm_client: LLMClient) -> Tuple[List[Chunk], float]:
    """Uses LLM to detect and fix header hierarchy issues."""
    logger.info("Correcting headers with LLM...")
    unique_headers = extract_unique_headers(chunks)
    if not unique_headers:
        return chunks, 0.0
    
    template = get_header_correction_template()
    prompt = template.render(headers=unique_headers)
    
    model = "gpt-5.2"
    try:
        response, cost = llm_client.chat_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=HeaderAnalysis,
            reasoning_effort="medium"
        )
        
        logger.info(f"Header correction completed | Cost: ${cost:.6f}")
        
        analysis = response.choices[0].message.parsed
        
        if not analysis.corrections:
            logger.info("LLM found no header corrections needed.")
            return chunks, cost
        
        logger.info(f"Applying {len(analysis.corrections)} corrections (Confidence: {analysis.confidence_level})")
        
        return apply_corrections(chunks, analysis.corrections), cost
        
    except Exception as e:
        logger.error(f"LLM header correction failed: {e}")
        return chunks, 0.0


def apply_corrections(chunks: List[Chunk], corrections: List) -> List[Chunk]:
    """
    Applies header level corrections with section-number-based re-parenting.
    
    Key insight: chunks are parsed in document order, but a parent header (like "1.0")
    may appear AFTER its children (like "1.1") in the PDF due to TOC/Appendix listings.
    This method uses section numbering (1.0 -> 1.1 -> 1.1.1) to determine hierarchy.
    """
    # Build correction maps
    correction_map = {
        (c.original_level, c.original_name): c.corrected_level
        for c in corrections
    }
    name_to_corrected = {c.original_name: c.corrected_level for c in corrections}
    
    # Helper: extract section number from header name (e.g., "1.1 Eligibility" -> "1.1")
    section_pattern = re.compile(r'^(\d+(?:\.\d+)*)')
    
    def get_section_number(name: str) -> Optional[str]:
        match = section_pattern.match(name)
        return match.group(1) if match else None
    
    def get_section_parent(section_num: str) -> Optional[str]:
        """Get the parent section number (e.g., "1.1.1" -> "1.1", "1.1" -> "1.0", "1.0" -> None)"""
        parts = section_num.split('.')
        if len(parts) <= 1:
            return None
        # "1.0" has no parent (it's a top-level section)
        if len(parts) == 2 and parts[1] == '0':
            return None
        # For "1.1" the parent is "1.0", for "1.1.1" the parent is "1.1"
        if len(parts) == 2:
            return f"{parts[0]}.0"
        return '.'.join(parts[:-1])
    
    # First pass: collect all unique headers and their corrected levels
    # Also build a section number -> header info map
    all_headers: Dict[str, Tuple[str, str]] = {}  # name -> (corrected_level, name)
    section_headers: Dict[str, Tuple[str, str]] = {}  # section_num -> (level, name)
    
    for chunk in chunks:
        for header in (chunk.header_path or []):
            name = header.name
            original_key = (header.level, name)
            
            # Get corrected level
            if original_key in correction_map:
                level = correction_map[original_key]
            elif name in name_to_corrected:
                level = name_to_corrected[name]
            else:
                level = header.level
            
            if name not in all_headers:
                all_headers[name] = (level, name)
                
                # Index by section number
                sec_num = get_section_number(name)
                if sec_num:
                    section_headers[sec_num] = (level, name)
    
    # Second pass: rebuild header paths for each chunk using section numbering
    for chunk in chunks:
        if not chunk.header_path:
            continue
        
        # Get the deepest (last) header in the chunk's path
        chunk_headers = chunk.header_path
        deepest_header = chunk_headers[-1] if chunk_headers else None
        
        if not deepest_header:
            continue
        
        # Get corrected info for the deepest header
        name = deepest_header.name
        original_key = (deepest_header.level, name)
        if original_key in correction_map:
            corrected_level = correction_map[original_key]
        elif name in name_to_corrected:
            corrected_level = name_to_corrected[name]
        else:
            corrected_level = deepest_header.level
        
        # Build ancestor chain using section numbering
        ancestors = []
        sec_num = get_section_number(name)
        
        if sec_num:
            # Walk up the section number hierarchy
            parent_num = get_section_parent(sec_num)
            while parent_num:
                if parent_num in section_headers:
                    parent_level, parent_name = section_headers[parent_num]
                    ancestors.insert(0, HeaderNode(level=parent_level, name=parent_name))
                parent_num = get_section_parent(parent_num) if parent_num and '.' in parent_num else None
        
        # Also include non-numbered headers from original path (like "Appendices" if it's a true parent)
        # But only keep them if they're at a higher level than our numbered headers
        numbered_min_level = 999
        if ancestors:
            numbered_min_level = min(int(h.level.split()[1]) for h in ancestors)
        elif sec_num:
            numbered_min_level = int(corrected_level.split()[1])
        
        # Include non-numbered ancestors only if they're higher level
        non_numbered_ancestors = []
        for header in chunk_headers[:-1]:  # Exclude deepest header
            sec = get_section_number(header.name)
            if not sec:  # Non-numbered header
                h_level = int(header.level.split()[1])
                if h_level < numbered_min_level:
                    # Only keep if this makes sense (e.g., document title)
                    # Skip "Appendices" as a false parent for numbered sections
                    if header.name.lower() not in ['appendices', 'contents']:
                        non_numbered_ancestors.append(header)
        
        # Combine: non-numbered ancestors + numbered ancestors + current header
        new_path = non_numbered_ancestors + ancestors + [
            HeaderNode(level=corrected_level, name=name)
        ]
        
        chunk.header_path = new_path
    
    return chunks


def build_header_tree(chunks: List[Chunk]) -> Dict:
    """Build hierarchical header tree from chunks."""
    tree = {}
    
    for chunk in chunks:
        if not chunk.header_path:
            continue
        
        current = tree
        for header in chunk.header_path:
            key = f"{header.level}:{header.name}"
            if key not in current:
                current[key] = {}
            current = current[key]
    
    return tree
