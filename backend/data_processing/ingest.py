"""
Data processing module for creating chunks from markdown documents.
"""

import os
import re
import uuid
import asyncio
from typing import List, Optional, Dict, Tuple, Set
from datetime import datetime

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
    get_section_summary_template
)

load_dotenv()

class DocumentIngestor:
    """
    Handles the ingestion of markdown documents, including:
    1. Splitting content by page and section (headers).
    2. Correcting header hierarchies using LLM.
    3. Merging sections for summarization.
    4. Splitting large sections for RAG embedding.
    5. Generating hierarchical summaries.
    """

    def __init__(self, fix_headers: bool = True, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.fix_headers = fix_headers
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Clients
        self.sync_client = OpenAI()
        self.async_client = AsyncOpenAI()

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
            
        # 1. Split by Page & Parse Headers
        split_content = self._split_by_page(markdown_text)
        processed_chunks = self._process_text_pages(split_content, doc_id)

        # 2. Correct headers (Optional)
        if self.fix_headers:
            processed_chunks = self._correct_headers(processed_chunks)
        
        # 3. Merge chunks (Section Chunks for Summaries)
        section_chunks = self._merge_sections(processed_chunks)
        
        # 4. Split chunks (RAG Chunks)
        rag_chunks = self._split_chunks(section_chunks)

        return IngestedDocument(
            id=doc_id,
            filename=filename,
            total_pages=len(split_content),
            chunks=rag_chunks,
            section_chunks=section_chunks
        )

    # --- Public Utilities ---

    async def generate_skeleton_summaries(
        self,
        chunks: List[ProcessedChunk],
        first_n_chars: int = 2500,
        last_n_chars: int = 1000
    ) -> Dict[tuple, str]:
        """
        Generate hierarchical summaries for sections, bottom-up.
        """
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
        
        # Helper component task
        async def _summarize_single(key: tuple, content: str, child_summaries: List[dict]) -> Tuple[tuple, str]:
            section_name = " > ".join([h[1] for h in key]) if key else "Document"
            content_start = content[:first_n_chars]
            content_end = content[-last_n_chars:] if len(content) > first_n_chars + last_n_chars else ""
            
            prompt = template.render(
                section_name=section_name,
                content_start=content_start,
                content_end=content_end,
                child_summaries=child_summaries
            )
            
            try:
                response = await self.async_client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format=SectionSummary
                )
                return key, response.choices[0].message.parsed.summary
            except Exception as e:
                print(f"Summary failed for {section_name}: {e}")
                return key, ""

        # Process levels
        for level in sorted_levels:
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
                for key, summary in results:
                    summaries[key] = summary
        
        return summaries

    def generate_skeleton_summaries_sync(
        self,
        chunks: List[ProcessedChunk],
        first_n_chars: int = 2500,
        last_n_chars: int = 1000
    ) -> Dict[tuple, str]:
        """Sync wrapper for generate_skeleton_summaries."""
        return asyncio.run(self.generate_skeleton_summaries(chunks, first_n_chars, last_n_chars))


    # --- Internal Helpers ---

    def _split_by_page(self, markdown_text: str) -> List[str]:
        """Splits markdown by the custom page delimiter."""
        page_split_pattern = r'\n\n\{\d+\}------------------------------------------------\n\n'
        # The split usually results in [empty_preamble, page_1, page_2...]
        return re.split(page_split_pattern, markdown_text)[1:]

    def _process_text_pages(self, pages: List[str], doc_id: str) -> List[ProcessedChunk]:
        """Processes each page text, extracting sections and headers."""
        chunks = []
        global_chunk_index = 0
        global_header_context = {}

        for i, page_text in enumerate(pages):
            curr_page = i + 1
            sections = self._parse_sections(page_text, initial_headers=global_header_context)
            
            if sections:
                global_header_context = sections[-1]['metadata'].copy()
            
            for section in sections:
                content = section['content']
                if not content: continue
                
                global_chunk_index += 1
                header_breadcrumbs = []
                for h_tag, h_name in section['metadata'].items():
                    header_breadcrumbs.append(SectionHeader(level=h_tag, name=h_name))

                chunks.append(ProcessedChunk(
                    document_id=doc_id,
                    content=content,
                    chunk_index=global_chunk_index,
                    location=ChunkLocation(page_number=curr_page),
                    header_path=header_breadcrumbs,
                    metadata=section['metadata']
                ))
        return chunks

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

    def _correct_headers(self, chunks: List[ProcessedChunk]) -> List[ProcessedChunk]:
        """Uses LLM to detect and fix header hierarchy issues."""
        print("Correcting headers with LLM...")
        unique_headers = self._extract_unique_headers(chunks)
        if not unique_headers:
            return chunks
        
        template = get_header_correction_template()
        prompt = template.render(headers=unique_headers)
        
        try:
            # Using sync block here as in original
            response = self.sync_client.beta.chat.completions.parse(
                model="gpt-5-mini", # Preserving user request for specific model name
                messages=[{"role": "user", "content": prompt}],
                response_format=HeaderAnalysis,
                reasoning_effort="low"
            )
            
            analysis = response.choices[0].message.parsed
            
            if not analysis.corrections:
                print("LLM found no header corrections needed.")
                return chunks
            
            print(f"LLM Analysis (confidence: {analysis.confidence_level}):")
            print(f"  Patterns: {analysis.observed_patterns}")
            print(f"  Issues: {analysis.identified_issues}")
            print(f"  Corrections: {len(analysis.corrections)}")
            for c in analysis.corrections:
                print(f"    - {c.original_name}: {c.original_level} -> {c.corrected_level}")
            
            return self._apply_corrections(chunks, analysis.corrections)
            
        except Exception as e:
            print(f"LLM header correction failed: {e}")
            return chunks

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
        correction_map = {
            (c.original_level, c.original_name): c.corrected_level
            for c in corrections
        }
        
        for chunk in chunks:
            if not chunk.header_path:
                continue
            
            new_headers = []
            for header in chunk.header_path:
                key = (header.level, header.name)
                if key in correction_map:
                    new_level = correction_map[key]
                    new_level_num = int(new_level.split()[1])
                    # Remove any headers at the same or higher level number (siblings/children logic)
                    new_headers = [h for h in new_headers if int(h.level.split()[1]) < new_level_num]
                    new_headers.append(SectionHeader(level=new_level, name=header.name))
                    
                    # Update metadata
                    chunk.metadata.pop(header.level, None)
                    chunk.metadata[new_level] = header.name
                else:
                    new_headers.append(header)
            chunk.header_path = new_headers
        
        return chunks

    def _merge_sections(self, chunks: List[ProcessedChunk]) -> List[ProcessedChunk]:
        """Merge consecutive chunks with the same header_path."""
        if not chunks: return []
        
        merged = [chunks[0]]
        for chunk in chunks[1:]:
            if self._get_header_key(merged[-1]) == self._get_header_key(chunk):
                merged[-1].content += chunk.content
            else:
                merged.append(chunk)
        
        # Re-index
        for i, chunk in enumerate(merged):
            chunk.chunk_index = i + 1
        return merged

    def _split_chunks(self, chunks: List[ProcessedChunk]) -> List[ProcessedChunk]:
        """Split large chunks into smaller ones."""
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        result = []
        for chunk in chunks:
            texts = splitter.split_text(chunk.content)
            for text in texts:
                result.append(ProcessedChunk(
                    document_id=chunk.document_id,
                    content=text,
                    chunk_index=0, # Placeholder
                    location=chunk.location,
                    header_path=chunk.header_path,
                    metadata=chunk.metadata.copy()
                ))
        
        # Re-index
        for i, chunk in enumerate(result):
            chunk.chunk_index = i + 1
        return result

    def _get_header_key(self, chunk: ProcessedChunk) -> tuple:
        if not chunk.header_path:
            return ()
        return tuple((h.level, h.name) for h in sorted(chunk.header_path, key=lambda h: int(h.level.split()[1])))


# --- Backwards Compatibility / Legacy Exports ---

def parse_markdown_to_chunks(
    markdown_text: str, 
    filename: str,
    images: Dict[str, str] = {}, # Kept for signature compatibility but ignored
    doc_id: Optional[str] = None,
    fix_headers: bool = False
) -> IngestedDocument:
    """Wrapper for DocumentIngestor to maintain legacy script compatibility."""
    ingestor = DocumentIngestor(fix_headers=fix_headers)
    return ingestor.ingest(markdown_text, filename, doc_id)

def generate_skeleton_summaries_sync(chunks, *args, **kwargs):
    """Wrapper for DocumentIngestor logic."""
    ingestor = DocumentIngestor()
    return ingestor.generate_skeleton_summaries_sync(chunks, *args, **kwargs)

# Exposed helpers if strictly needed by tests
# (Usually tests can update to use the class, but keeping them if needed)
def simple_markdown_splitter(*args, **kwargs):
    ingestor = DocumentIngestor()
    return ingestor._parse_sections(*args, **kwargs)