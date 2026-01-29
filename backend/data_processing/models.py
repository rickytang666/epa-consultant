import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Annotated
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

@dataclass
class SectionHeader:
    """Captures the hierarchical header context (e.g., H1 -> H2)."""
    level: str
    name: str

    def to_dict(self) -> Dict[str, str]:
        return {"level": self.level, "name": self.name}

@dataclass
class ChunkLocation:
    """Physical location of the text in the original document."""
    page_number: int

    def to_dict(self) -> Dict[str, int]:
        return {"page_number": self.page_number}


@dataclass
class ProcessedChunk:
    """
    The Atomic Unit of your RAG.
    """
    document_id: str
    content: str 
    chunk_index: Any # Can be int or str (e.g. "1-0")
    location: ChunkLocation
    
    # Breadcrumbs
    header_path: List[SectionHeader] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "location": self.location.to_dict(),
            "header_path": [h.to_dict() for h in self.header_path],
            "metadata": self.metadata
        }

@dataclass
class IngestedDocument:
    """The container for the full paper analysis."""
    document_id: str
    filename: str
    total_pages: int
    chunks: List[ProcessedChunk]  # Small chunks for RAG
    
    # Summaries (Sprint 2 placeholder)
    document_summary: str = ""
    section_summaries: Dict[str, str] = field(default_factory=dict)
    
    section_chunks: List[ProcessedChunk] = field(default_factory=list)  # Large merged chunks for summaries
    
    costs: Dict[str, float] = field(default_factory=dict)
    
    ingested_at: datetime = field(default_factory=datetime.utcnow)

    def _build_header_tree(self) -> Dict:
        """Build nested dict of headers from chunks."""
        tree = {}
        for chunk in self.chunks:
            if not chunk.header_path:
                continue
            current = tree
            for header in chunk.header_path:
                name = header.name
                if name not in current:
                    current[name] = {}
                current = current[name]
        return tree

    def to_dict(self) -> Dict[str, Any]:
        # Convert tuple keys to string for JSON
        str_summaries = {}
        for key, val in self.section_summaries.items():
            if isinstance(key, tuple):
                str_key = " > ".join([h[1] for h in key])
            else:
                str_key = str(key)
            str_summaries[str_key] = val
        
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "document_summary": self.document_summary,
            "section_summaries": str_summaries,
            "header_tree": self._build_header_tree(),
            "costs": self.costs,
            "chunks": [c.to_dict() for c in self.chunks]
        }


class HeaderCorrection(BaseModel):
    """A single header correction."""
    reason: Annotated[str, Field(description="Short 2-3 sentences analysis")]
    corrected: Annotated[bool, Field(description="Whether a correction will be applied")]
    original_level: str  # e.g., "Header 4"
    original_name: str
    corrected_level: str  # e.g., "Header 3"


class HeaderAnalysis(BaseModel):
    """Structured output for header hierarchy analysis."""
    # Reasoning fields to encourage better analysis
    observed_patterns: str  # What patterns does the LLM see?
    identified_issues: str  # What inconsistencies were found?
    confidence_level: str
    
    # Final corrections
    corrections: List[HeaderCorrection]


class SectionSummary(BaseModel):
    """Structured output for section summary."""
    key_topics: str
    summary: str