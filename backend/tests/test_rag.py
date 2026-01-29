import pytest
from unittest.mock import patch, MagicMock
from ml.rag_pipeline import query_rag

def test_query_rag_mocked():
    """test rag pipeline logic with mocks"""
    
    with patch("ml.rag_pipeline.retrieve_relevant_chunks") as mock_retrieval, \
         patch("ml.rag_pipeline.or_client") as mock_openai:
        
        # setup retrieval mock
        mock_retrieval.return_value = [
            {"text": "EPA regulates pesticides through the FIFRA act.", "metadata": {}},
            {"text": "Safety standards are paramount.", "metadata": {}}
        ]
        
        # setup openai mock
        # we act as if openai client is present
        # create a mock stream
        mock_chunk1 = MagicMock()
        mock_chunk1.choices[0].delta.content = "The "
        mock_chunk2 = MagicMock()
        mock_chunk2.choices[0].delta.content = "EPA "
        mock_chunk3 = MagicMock()
        mock_chunk3.choices[0].delta.content = "regulates."
        
        mock_openai.chat.completions.create.return_value = [mock_chunk1, mock_chunk2, mock_chunk3]
        
        # execute
        generator = query_rag("What does EPA regulate?")
        response = "".join(list(generator))
        
        # verify
        assert "The EPA regulates." in response
        mock_retrieval.assert_called_once()
        mock_openai.chat.completions.create.assert_called_once()
