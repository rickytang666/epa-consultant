import sys
import os
# add backend to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import patch, MagicMock
from ml.retrieval import retrieve_relevant_chunks

@patch("ml.retrieval.get_embedding")
@patch("ml.retrieval.search_chunks")
@pytest.mark.asyncio
async def test_retrieve_relevant_chunks(mock_search, mock_embedding):
    """test high level retrieval flow"""
    
    # mock embedding return
    # dim 1536
    mock_embedding.return_value = [0.1] * 1536
    
    # mock search return
    mock_search.return_value = [
        {"chunk_id": "1", "text": "result 1", "metadata": {}},
        {"chunk_id": "2", "text": "result 2", "metadata": {}}
    ]
    
    results = await retrieve_relevant_chunks("test query", n_results=2)
    
    # verify calls
    mock_embedding.assert_called_once_with("test query")
    mock_search.assert_called_once()
    
    # check args passed to search (embedding and n_results)
    args, kwargs = mock_search.call_args
    assert kwargs['n_results'] == 4 # implementation fetches 2x for fusion
    assert kwargs['query_embedding'] == [0.1] * 1536
    
    # verify output
    assert len(results) == 2
    assert results[0]["text"] == "result 1"

@pytest.mark.asyncio
async def test_retrieve_empty_query():
    """test empty query returns empty list early"""
    results = await retrieve_relevant_chunks("")
    assert results == []
