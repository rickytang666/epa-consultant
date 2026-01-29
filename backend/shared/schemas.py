"""shared data schemas for the entire backend"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# document-level schemas
# ============================================================================

class HeaderNode(BaseModel):
    """header in the document hierarchy"""
    level: str  # "Header 1", "Header 2", etc.
    name: str


class ChunkLocation(BaseModel):
    """location of chunk in source document"""
    page_number: int


class ChunkMetadata(BaseModel):
    """metadata for a chunk"""
    is_table: bool = False
    table_id: Optional[str] = None
    table_title: Optional[str] = None


class Chunk(BaseModel):
    """single chunk of text or table"""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    location: ChunkLocation
    header_path: List[HeaderNode]
    metadata: ChunkMetadata


class ProcessedDocument(BaseModel):
    """complete processed document with chunks"""
    document_id: str
    filename: str
    document_summary: str = ""
    section_summaries: Dict[str, str] = Field(default_factory=dict)
    header_tree: Dict[str, Any] = Field(default_factory=dict)
    costs: Optional[Dict[str, float]] = None
    chunks: List[Chunk]


# ============================================================================
# table schemas
# ============================================================================

class TableMetadata(BaseModel):
    """metadata for a table"""
    section: Optional[str] = None
    row_count: int
    col_count: int


class Table(BaseModel):
    """structured table data"""
    table_id: str
    title: str
    page: int
    markdown: str
    headers: List[str]
    rows: List[List[str]]
    metadata: TableMetadata


class TablesDocument(BaseModel):
    """collection of tables from a document"""
    document_id: str
    filename: str
    tables: List[Table]
