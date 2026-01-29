"""
LLM-based summarization for sections and documents (Sprint 2 feature).
"""

import asyncio
import logging
from typing import List, Dict, Tuple

from .models import SectionSummary
from .prompts import get_section_summary_template, get_document_summary_template
from .llm_client import LLMClient
from shared.schemas import Chunk

logger = logging.getLogger(__name__)


def get_header_key(chunk: Chunk) -> tuple:
    """extract header key from chunk for grouping"""
    if not chunk.header_path:
        return ()
    return tuple((h.level, h.name) for h in sorted(chunk.header_path, key=lambda h: int(h.level.split()[1])))


def get_section_preview_lazy(chunks: List[Chunk], first_n: int = 2500, last_n: int = 1000) -> tuple[str, str]:
    """smart sampling: avoids duplication for short sections (10-20% token savings)"""
    if not chunks:
        return "", ""
    
    # calculate total content length first
    total_content_len = sum(len(c.content) for c in chunks)
    
    # smart sampling: if section is short, don't duplicate content
    if total_content_len <= first_n + last_n:
        # section fits in budget, return all content (no duplication)
        return ''.join(c.content for c in chunks), ""
    
    # section is long, use split sampling
    # collect start content
    start_parts = []
    start_len = 0
    for chunk in chunks:
        if start_len >= first_n:
            break
        remaining = first_n - start_len
        start_parts.append(chunk.content[:remaining])
        start_len += len(start_parts[-1])
    
    # collect end content (reverse iteration)
    end_parts = []
    end_len = 0
    for chunk in reversed(chunks):
        if end_len >= last_n:
            break
        remaining = last_n - end_len
        end_parts.insert(0, chunk.content[-remaining:])
        end_len += len(end_parts[0])
    
    return ''.join(start_parts), ''.join(end_parts)


def build_hierarchy_index(section_keys: List[tuple]) -> Dict[tuple, List[tuple]]:
    """pre-compute parent-child relationships for O(1) lookups (replaces O(n²) nested loops)"""
    from collections import defaultdict
    
    parent_to_children = defaultdict(list)
    
    for key in section_keys:
        if len(key) > 0:
            # parent is the key without the last element
            parent_key = key[:-1] if len(key) > 1 else ()
            parent_to_children[parent_key].append(key)
    
    return dict(parent_to_children)


async def generate_section_summaries(
    chunks: List[Chunk],
    llm_client: LLMClient,
    first_n_chars: int = 2500,
    last_n_chars: int = 1000
) -> Tuple[Dict[tuple, str], float]:
    """
    Generate hierarchical summaries for sections, bottom-up.
    """
    logger.info("Starting skeleton summary generation...")
    template = get_section_summary_template()
    
    # group chunks by header_path (no concatenation yet)
    sections: Dict[tuple, List[Chunk]] = {}
    for chunk in chunks:
        key = get_header_key(chunk)
        if key not in sections:
            sections[key] = []
        sections[key].append(chunk)
    
    # Find unique levels
    levels = set()
    for key in sections:
        if key:
            # Key[-1] is the last header in path: (Level, Name)
            last_header_level = key[-1][0]  # e.g., "Header 3"
            level_num = int(last_header_level.split()[1])
            levels.add(level_num)
    
    sorted_levels = sorted(levels, reverse=True)  # deepest first
    summaries: Dict[tuple, str] = {}
    total_cost = 0.0
    
    # build hierarchy index once for O(1) child lookups (replace nested loops)
    hierarchy = build_hierarchy_index(list(sections.keys()))
    
    # helper: summarize single section
    async def _summarize_single(key: tuple, section_chunks: List[Chunk], child_summaries: List[dict]) -> Tuple[tuple, str, float]:
        section_name = " > ".join([h[1] for h in key]) if key else "document"
        
        # lazy sampling: only process what we need
        content_start, content_end = get_section_preview_lazy(section_chunks, first_n_chars, last_n_chars)
        
        prompt = template.render(
            section_name=section_name,
            content_start=content_start,
            content_end=content_end,
            child_summaries=child_summaries
        )
        
        model = "gpt-5-mini"
        try:
            response, cost = await llm_client.async_chat_completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=SectionSummary
            )
            
            logger.info(f"Summarized '{section_name}'")
            
            return key, response.choices[0].message.parsed.summary, cost
        except Exception as e:
            logger.error(f"Summary failed for {section_name}: {e}")
            return key, "", 0.0

    # Process levels
    for level in sorted_levels:
        logger.info(f"Processing Level {level}...")
        # Get all sections at this level
        level_sections = [
            (k, v) for k, v in sections.items() 
            if k and int(k[-1][0].split()[1]) == level
        ]
        
        tasks = []
        for key, section_chunks in level_sections:
            # O(1) lookup for direct children using pre-computed index
            child_keys = hierarchy.get(key, [])
            child_sums = [
                {"name": child_key[-1][1], "summary": summaries[child_key]}
                for child_key in child_keys
                if child_key in summaries
            ]
            
            tasks.append(_summarize_single(key, section_chunks, child_sums))
        
        if tasks:
            results = await asyncio.gather(*tasks)
            for key, summary, cost in results:
                summaries[key] = summary
                total_cost += cost
    
    logger.info(f"Summary generation complete. Total Cost: ${total_cost:.4f}")
    return summaries, total_cost


def generate_section_summaries_sync(
    chunks: List[Chunk],
    llm_client: LLMClient,
    first_n_chars: int = 2500,
    last_n_chars: int = 1000
) -> Tuple[Dict[tuple, str], float]:
    """Sync wrapper for generate_section_summaries."""
    return asyncio.run(generate_section_summaries(chunks, llm_client, first_n_chars, last_n_chars))


def generate_document_summary(
    section_summaries: Dict[tuple, str],
    llm_client: LLMClient,
    filename: str = ""
) -> Tuple[str, float]:
    """Generate a 2-8 sentence document summary from skeleton summaries."""
    if not section_summaries:
        return "", 0.0
    
    # Build sections list for template
    sections = []
    for key, summary in section_summaries.items():
        if not summary:
            continue
        if isinstance(key, tuple):
            name = ' > '.join([h[1] for h in key])
        else:
            name = str(key)
        sections.append({"name": name, "summary": summary})
    
    template = get_document_summary_template()
    prompt = template.render(filename=filename, sections=sections)
    
    model = "gpt-5-mini"
    try:
        response, cost = llm_client.chat_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            reasoning_effort="low"
        )
        content = response.choices[0].message.content or ""
        logger.info(f"Document Summary | Cost: ${cost:.6f}")
        return content.strip(), cost
    except Exception as e:
        logger.error(f"Document summary failed: {e}")
        return "", 0.0
