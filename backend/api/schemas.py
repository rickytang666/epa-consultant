"""pydantic models for api"""

from pydantic import BaseModel
from typing import List, Dict, Any


class QueryRequest(BaseModel):
    """request model for /query endpoint"""
    question: str


class QueryResponse(BaseModel):
    """response model for /query endpoint"""
    answer: str
    sources: List[Dict[str, Any]] = []


class TableResponse(BaseModel):
    """response model for /tables endpoint"""
    tables: List[Dict[str, Any]]
