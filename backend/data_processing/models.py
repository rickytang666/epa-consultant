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
    start_char_index: Optional[int] = None 
    end_char_index: Optional[int] = None


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
    chunks: List[ProcessedChunk]
    ingested_at: datetime = field(default_factory=datetime.utcnow)