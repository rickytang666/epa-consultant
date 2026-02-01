
import os
import sys
import pytest
from dotenv import load_dotenv

# setup path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.rag_pipeline import query_rag

# load env vars once
load_dotenv()

@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_type", [
    ("Hello there!", "supplemental"),
    ("What are the rules for mosquito control?", "core"),
    ("Thanks for your help.", "supplemental"),
    ("When does the permit expire?", "core")
])
async def test_router_classification(query, expected_type):
    """verify router correctly classifies intent (core=sources present, supplemental=no sources)"""
    has_sources = False
    
    async for chunk in query_rag(query):
        if chunk['type'] == 'sources':
            has_sources = True
            break # stop early if sources found
    
    is_core = has_sources
    assert (expected_type == "core") == is_core, f"failed for query: {query}"
