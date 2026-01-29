from typing import List, Annotated
from pydantic import BaseModel, Field

# import shared schemas - single source of truth
from shared.schemas import (
    HeaderNode,
    ChunkLocation,
    Chunk,
    ChunkMetadata,
    ProcessedDocument
)

# LLM-specific models for data processing only


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