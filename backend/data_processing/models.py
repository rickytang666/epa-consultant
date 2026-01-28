import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

@dataclass
class SectionHeader:
    """Captures the hierarchical header context (e.g., H1 -> H2)."""
    level: str
    name: str

@dataclass
class ChunkLocation:
    """Physical location of the text in the original document."""
    page_number: int



@dataclass
class ProcessedChunk:
    """
    The Atomic Unit of your RAG.
    """
    document_id: str
    content: str 
    chunk_index: int
    location: ChunkLocation
    
    # Breadcrumbs
    header_path: List[SectionHeader] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class IngestedDocument:
    """The container for the full paper analysis."""
    id: str
    filename: str
    total_pages: int
    chunks: List[ProcessedChunk]  # Small chunks for RAG
    section_chunks: List[ProcessedChunk] = field(default_factory=list)  # Large merged chunks for summaries
    ingested_at: datetime = field(default_factory=datetime.utcnow)


# Pydantic models for LLM structured output
from pydantic import BaseModel

class HeaderCorrection(BaseModel):
    """A single header correction."""
    original_level: str  # e.g., "Header 4"
    original_name: str
    corrected_level: str  # e.g., "Header 3"
    reason: str


class HeaderAnalysis(BaseModel):
    """Structured output for header hierarchy analysis."""
    # Reasoning fields to encourage better analysis
    observed_patterns: str  # What patterns does the LLM see?
    identified_issues: str  # What inconsistencies were found?
    confidence_level: str  # "high", "medium", or "low"
    
    # Final corrections
    corrections: List[HeaderCorrection]


class SectionSummary(BaseModel):
    """Structured output for section summary."""
    key_topics: str  # Main topics covered
    summary: str  # 1-4 sentence summary