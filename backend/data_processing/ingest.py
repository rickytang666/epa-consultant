"""
Main document ingestion orchestrator.
"""

import uuid
import logging
from typing import Optional
from dotenv import load_dotenv

from shared.schemas import ProcessedDocument
from .llm_client import LLMClient
from .parsing import split_by_page, process_text_pages
from .chunking import merge_chunks, split_chunks
from .header_correction import correct_headers, build_header_tree
from .summarization import generate_section_summaries, generate_section_summaries_sync, generate_document_summary

load_dotenv()

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DocumentIngestor:
    """
    Handles the ingestion of markdown documents.
    """

    def __init__(self, fix_headers: bool = True, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.fix_headers = fix_headers
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # LLM client with fallback
        self.llm_client = LLMClient()

    def ingest(
        self, 
        markdown_text: str, 
        filename: str, 
        doc_id: Optional[str] = None
    ) -> ProcessedDocument:
        """
        Main synchronous entry point for document ingestion.
        """
        if doc_id is None:
            doc_id = str(uuid.uuid4())
            
        logger.info(f"Starting ingestion for file: {filename} (ID: {doc_id})")

        # 1. Split by Page & Parse Headers
        split_content = split_by_page(markdown_text)
        processed_chunks = process_text_pages(split_content, doc_id)
        logger.info(f"Extracted {len(processed_chunks)} raw text chunks from {len(split_content)} pages.")

        # 2. Correct headers (Optional)
        costs = {}
        if self.fix_headers:
            processed_chunks, correction_cost = correct_headers(processed_chunks, self.llm_client)
            costs["header_correction"] = correction_cost
            logger.info(f"Header Correction Cost: ${correction_cost:.6f}")
        
        # 3. Merge chunks (Section Chunks for Summaries)
        section_chunks = merge_chunks(processed_chunks, self.chunk_size)
        logger.info(f"Merged into {len(section_chunks)} section chunks.")
        
        # 4. Split chunks (RAG Chunks)
        rag_chunks = split_chunks(section_chunks, self.chunk_size, self.chunk_overlap)
        logger.info(f"Split into {len(rag_chunks)} final RAG chunks.")

        logger.info("Ingestion complete.")
        
        # Build header tree from chunks
        header_tree = build_header_tree(rag_chunks)
        
        return ProcessedDocument(
            document_id=doc_id,
            filename=filename,
            chunks=rag_chunks,
            document_summary="",
            section_summaries={},
            header_tree=header_tree,
            costs={
                "header_correction": costs.get("header_correction", 0.0),
                "skeleton_summaries": 0.0,
                "total": costs.get("header_correction", 0.0)
            }
        )

    # --- Public Utilities (Sprint 2 features) ---

    async def generate_skeleton_summaries(self, chunks, first_n_chars=2500, last_n_chars=1000):
        """Generate hierarchical summaries for sections, bottom-up."""
        return await generate_section_summaries(chunks, self.llm_client, first_n_chars, last_n_chars)

    def generate_skeleton_summaries_sync(self, chunks, first_n_chars=2500, last_n_chars=1000):
        """Sync wrapper for generate_skeleton_summaries."""
        return generate_section_summaries_sync(chunks, self.llm_client, first_n_chars, last_n_chars)

    def generate_document_summary(self, section_summaries, filename=""):
        """Generate a 2-8 sentence document summary from skeleton summaries."""
        return generate_document_summary(section_summaries, self.llm_client, filename)
