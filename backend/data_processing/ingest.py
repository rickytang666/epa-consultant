"""
Data processing module for creating chunks from markdown documents.
"""

import os
import re
import uuid
import asyncio
import logging
from typing import List, Optional, Dict, Tuple, Set
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter

from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

from .models import (
    IngestedDocument, 
    ProcessedChunk, 
    ChunkLocation, 
    SectionHeader,
    HeaderAnalysis,
    SectionSummary
)
from .prompts import (
    get_header_correction_template,
    get_section_summary_template,
    get_document_summary_template
)

load_dotenv()

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pricing constants (per 1M tokens)
PRICING = {
    "gpt-5-mini": {"input": 0.25, "output": 2.0},
    "default": {"input": 0.25, "output": 2.0}
}

class DocumentIngestor:
    """
    Handles the ingestion of markdown documents.
    """

    def __init__(self, fix_headers: bool = True, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.fix_headers = fix_headers
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Clients
        self.sync_client = OpenAI()
        self.async_client = AsyncOpenAI()
        self.total_cost = 0.0

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        price = PRICING.get(model, PRICING["default"])
        input_cost = (input_tokens / 1_000_000) * price["input"]
        output_cost = (output_tokens / 1_000_000) * price["output"]
        cost = input_cost + output_cost
        self.total_cost += cost
        return cost

    def ingest(
        self, 
        markdown_text: str, 
        filename: str, 
        doc_id: Optional[str] = None
    ) -> IngestedDocument:
        """
        Main synchronous entry point for document ingestion.
        """
        if doc_id is None:
            doc_id = str(uuid.uuid4())
            
        logger.info(f"Starting ingestion for file: {filename} (ID: {doc_id})")

        # 1. Split by Page & Parse Headers
        split_content = self._split_by_page(markdown_text)
        processed_chunks = self._process_text_pages(split_content, doc_id)
        logger.info(f"Extracted {len(processed_chunks)} raw text chunks from {len(split_content)} pages.")

        # 2. Correct headers (Optional)
        costs = {}
        if self.fix_headers:
            processed_chunks, correction_cost = self._correct_headers(processed_chunks)
            costs["header_correction"] = correction_cost
            logger.info(f"Header Correction Cost: ${correction_cost:.6f}")
        
        # 3. Merge chunks (Section Chunks for Summaries)
        section_chunks = self._merge_sections(processed_chunks)
        logger.info(f"Merged into {len(section_chunks)} section chunks.")
        
        # 4. Split chunks (RAG Chunks)
        rag_chunks = self._split_chunks(section_chunks)
        logger.info(f"Split into {len(rag_chunks)} final RAG chunks.")

        logger.info("Ingestion complete.")
        return IngestedDocument(
            document_id=doc_id,
            filename=filename,
            total_pages=len(split_content),
            chunks=rag_chunks,
            section_chunks=section_chunks,
            # Placeholders for future summary integration
            document_summary="",
            section_summaries={},
            costs={
                "header_correction": costs.get("header_correction", 0.0),
                "skeleton_summaries": 0.0,
                "total": costs.get("header_correction", 0.0)
            }
        )

    # --- Public Utilities ---

    async def generate_skeleton_summaries(
        self,
        chunks: List[ProcessedChunk],
        first_n_chars: int = 2500,
        last_n_chars: int = 1000
    ) -> Tuple[Dict[tuple, str], float]:
        """
        Generate hierarchical summaries for sections, bottom-up.
        """
        logger.info("Starting skeleton summary generation...")
        template = get_section_summary_template()
        
        # Group chunks by header_path
        sections: Dict[tuple, str] = {}
        for chunk in chunks:
            key = self._get_header_key(chunk)
            if key not in sections:
                sections[key] = chunk.content
            else:
                sections[key] += chunk.content
        
        # Find unique levels
        levels = set()
        for key in sections:
            if key:
                # Key[-1] is the last header in path: (Level, Name)
                last_header_level = key[-1][0]  # e.g., "Header 3"
                level_num = int(last_header_level.split()[1])
                levels.add(level_num)
        
        sorted_levels = sorted(levels, reverse=True) # Deepest first
        summaries: Dict[tuple, str] = {}
        total_cost = 0.0
        
        # Helper component task
        async def _summarize_single(key: tuple, content: str, child_summaries: List[dict]) -> Tuple[tuple, str, float]:
            section_name = " > ".join([h[1] for h in key]) if key else "Document"
            content_start = content[:first_n_chars]
            content_end = content[-last_n_chars:] if len(content) > first_n_chars + last_n_chars else ""
            
            prompt = template.render(
                section_name=section_name,
                content_start=content_start,
                content_end=content_end,
                child_summaries=child_summaries
            )
            
            model = "gpt-5-mini"
            try:
                response = await self.async_client.beta.chat.completions.parse(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=SectionSummary
                )
                
                usage = response.usage
                cost = self._calculate_cost(model, usage.prompt_tokens, usage.completion_tokens)
                logger.info(f"Summarized '{section_name}' | Tokens: {usage.prompt_tokens} in, {usage.completion_tokens} out | Cost: ${cost:.6f}")
                
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
            for key, content in level_sections:
                # Find direct children summaries
                child_sums = []
                for child_key, child_summary in summaries.items():
                    # Check if child_key starts with key (is a child) and is deeper
                    if child_key and len(child_key) > len(key) and child_key[:len(key)] == key:
                        child_sums.append({"name": child_key[-1][1], "summary": child_summary})
                
                tasks.append(_summarize_single(key, content, child_sums))
            
            if tasks:
                results = await asyncio.gather(*tasks)
                for key, summary, cost in results:
                    summaries[key] = summary
                    total_cost += cost
        
        logger.info(f"Summary generation complete. Total Cost: ${total_cost:.4f}")
        return summaries, total_cost

    def generate_skeleton_summaries_sync(
        self,
        chunks: List[ProcessedChunk],
        first_n_chars: int = 2500,
        last_n_chars: int = 1000
    ) -> Tuple[Dict[tuple, str], float]:
        """Sync wrapper for generate_skeleton_summaries."""
        return asyncio.run(self.generate_skeleton_summaries(chunks, first_n_chars, last_n_chars))

    def generate_document_summary(
        self,
        section_summaries: Dict[tuple, str],
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
            response = self.sync_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                reasoning_effort="low"
            )
            usage = response.usage
            cost = self._calculate_cost(model, usage.prompt_tokens, usage.completion_tokens)
            content = response.choices[0].message.content or ""
            logger.info(f"Document Summary | Cost: ${cost:.6f}")
            return content.strip(), cost
        except Exception as e:
            logger.error(f"Document summary failed: {e}")
            return "", 0.0


    # --- Internal Helpers ---

    def _split_by_page(self, markdown_text: str) -> List[str]:
        """Splits markdown by the custom page delimiter."""
        page_split_pattern = r'\n\n\{\d+\}------------------------------------------------\n\n'
        # The split usually results in [empty_preamble, page_1, page_2...]
        return re.split(page_split_pattern, markdown_text)[1:]

    def _process_text_pages(self, pages: List[str], doc_id: str) -> List[ProcessedChunk]:
        """Processes each page text, extracting sections, headers, and tables."""
        chunks = []
        global_chunk_index = 0
        global_header_context = {}

        for i, page_text in enumerate(pages):
            curr_page = i + 1
            
            # 1. Parse sections first (so we know headers)
            sections = self._parse_sections(page_text, initial_headers=global_header_context)
            
            if sections:
                global_header_context = sections[-1]['metadata'].copy()
            
            for section in sections:
                original_content = section['content']
                if not original_content: continue
                
            # 2. Extract tables from THIS section's content
                text_with_placeholders, table_blocks = self._extract_tables(original_content)
                
                # Setup metadata/headers common to both
                section_metadata = section['metadata']
                header_breadcrumbs = []
                for h_tag, h_name in section_metadata.items():
                    header_breadcrumbs.append(SectionHeader(level=h_tag, name=h_name))

                # 3. Create chunks in ORDER based on placeholders
                # Split text by table placeholders to maintain flow
                # We use a regex to split, keeping the delimiters (placeholders)
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
                            global_chunk_index += 1
                            table_meta = section_metadata.copy()
                            table_meta["type"] = "table"
                            chunks.append(ProcessedChunk(
                                document_id=doc_id,
                                content=table_blocks[table_idx],
                                chunk_index=global_chunk_index,
                                location=ChunkLocation(page_number=curr_page),
                                header_path=header_breadcrumbs,
                                is_table=True,
                                metadata=table_meta
                            ))
                    else:
                        # It's text
                        global_chunk_index += 1
                        chunks.append(ProcessedChunk(
                            document_id=doc_id,
                            content=part.strip(),
                            chunk_index=global_chunk_index,
                            location=ChunkLocation(page_number=curr_page),
                            header_path=header_breadcrumbs,
                            metadata=section_metadata
                        ))
        
        return chunks

    def _extract_tables(self, text: str) -> Tuple[str, List[str]]:
        """
        Extracts markdown tables from text.
        Returns: (text_with_placeholders, list_of_table_strings)
        """
        lines = text.split('\n')
        new_lines = []
        tables = []
        current_table = []
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            # Simple heuristic: markdown table lines start with |
            if stripped.startswith('|'):
                in_table = True
                current_table.append(line)
            else:
                if in_table:
                    # End of table
                    table_content = "\n".join(current_table)
                    tables.append(table_content)
                    current_table = []
                    in_table = False
                    # Insert placeholder
                    new_lines.append(f"__TABLE_{len(tables)-1}__")
                
                new_lines.append(line)
        
        # Catch last table
        if in_table and current_table:
            tables.append("\n".join(current_table))
            new_lines.append(f"__TABLE_{len(tables)-1}__")
            
        return "\n".join(new_lines), tables

    def _parse_sections(self, text: str, initial_headers: Optional[Dict[str, str]] = None) -> List[Dict]:
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

    def _correct_headers(self, chunks: List[ProcessedChunk]) -> Tuple[List[ProcessedChunk], float]:
        """Uses LLM to detect and fix header hierarchy issues."""
        logger.info("Correcting headers with LLM...")
        unique_headers = self._extract_unique_headers(chunks)
        if not unique_headers:
            return chunks, 0.0
        
        template = get_header_correction_template()
        prompt = template.render(headers=unique_headers)
        
        model = "gpt-5.2" # Using user preference
        try:
            response = self.sync_client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=HeaderAnalysis,
                reasoning_effort="medium"
            )
            
            usage = response.usage
            cost = self._calculate_cost(model, usage.prompt_tokens, usage.completion_tokens)
            logger.info(f"Header Correction Analysis | Tokens: {usage.prompt_tokens} in, {usage.completion_tokens} out | Cost: ${cost:.6f}")
            
            analysis = response.choices[0].message.parsed
            
            # # for debugging
            # with open("data/extracted/header_analysis.json", "w") as f:
            #     f.write(analysis.model_dump_json(indent=2
            # with open("data/extracted/header_analysis.json", "r") as f:
            #     analysis = HeaderAnalysis.model_validate_json(f.read())

            cost = 0.0  # Using cached analysis
            if not analysis.corrections:
                logger.info("LLM found no header corrections needed.")
                return chunks, cost
            
            logger.info(f"Applying {len(analysis.corrections)} corrections (Confidence: {analysis.confidence_level})")
            
            return self._apply_corrections(chunks, analysis.corrections), cost
            
        except Exception as e:
            logger.error(f"LLM header correction failed: {e}")
            return chunks, 0.0

    def _extract_unique_headers(self, chunks: List[ProcessedChunk]) -> List[tuple]:
        seen = set()
        unique = []
        for chunk in chunks:
            for header in (chunk.header_path or []):
                key = (header.level, header.name)
                if key not in seen:
                    seen.add(key)
                    unique.append(key)
        return unique

    def _apply_corrections(self, chunks: List[ProcessedChunk], corrections: List) -> List[ProcessedChunk]:
        """
        Applies header level corrections with section-number-based re-parenting.
        
        Key insight: chunks are parsed in document order, but a parent header (like "1.0")
        may appear AFTER its children (like "1.1") in the PDF due to TOC/Appendix listings.
        This method uses section numbering (1.0 -> 1.1 -> 1.1.1) to determine hierarchy.
        """
        import re
        
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
                        ancestors.insert(0, SectionHeader(level=parent_level, name=parent_name))
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
                SectionHeader(level=corrected_level, name=name)
            ]
            
            chunk.header_path = new_path
            chunk.metadata = {h.level: h.name for h in new_path}
        
        return chunks

    def _merge_sections(self, chunks: List[ProcessedChunk]) -> List[ProcessedChunk]:
        """
        Merges small chunks that belong to the same header section.
        """
        if not chunks:
            return []
            
        merged = []
        current_chunk = chunks[0]
        
        for next_chunk in chunks[1:]:
            # If next chunk is a table, don't merge it into text!
            if next_chunk.metadata.get("type") == "table":
                if current_chunk: # Flush any accumulated text chunk
                    merged.append(current_chunk)
                merged.append(next_chunk) 
                current_chunk = None # Reset current_chunk as we just added a table
                continue

            if current_chunk is None: # If previous was a table, start new accumulation
                current_chunk = next_chunk
                continue

            # Check matching headers
            headers_match = (current_chunk.header_path == next_chunk.header_path)
            
            # Check size limit
            combined_len = len(current_chunk.content) + len(next_chunk.content) + 1
            size_ok = combined_len < self.chunk_size
            
            if headers_match and size_ok:
                current_chunk.content += "\n" + next_chunk.content
                # Update location range if needed (simplified here)
            else:
                merged.append(current_chunk)
                current_chunk = next_chunk
        
        if current_chunk:
            merged.append(current_chunk)
            
        return merged

    def _split_chunks(self, chunks: List[ProcessedChunk]) -> List[ProcessedChunk]:
        """Splits chunks that are too large."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        final_chunks = []
        for chunk in chunks:
            # SKIP splitting for tables
            if chunk.metadata.get("type") == "table":
                final_chunks.append(chunk)
                continue
                
            if len(chunk.content) > self.chunk_size:
                split_texts = text_splitter.split_text(chunk.content)
                for i, text in enumerate(split_texts):
                    new_chunk = ProcessedChunk(
                        document_id=chunk.document_id,
                        content=text,
                        chunk_index=f"{chunk.chunk_index}-{i}",
                        location=chunk.location,
                        header_path=chunk.header_path,
                        metadata=chunk.metadata
                    )
                    final_chunks.append(new_chunk)
            else:
                final_chunks.append(chunk)
        
        return final_chunks

    def _get_header_key(self, chunk: ProcessedChunk) -> tuple:
        if not chunk.header_path:
            return ()
        return tuple((h.level, h.name) for h in sorted(chunk.header_path, key=lambda h: int(h.level.split()[1])))



