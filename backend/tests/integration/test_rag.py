import pytest
from unittest.mock import patch, MagicMock
from ml.rag_pipeline import query_rag_sync

def test_query_rag_mocked():
    """test rag pipeline logic with mocks"""
    
    with patch("ml.rag_pipeline.retrieve_relevant_chunks") as mock_retrieval, \
         patch("ml.rag_pipeline._get_llm") as mock_get_llm:
        
        # setup retrieval mock
        mock_retrieval.return_value = [
            {"text": "EPA regulates pesticides through the FIFRA act.", "metadata": {}},
            {"text": "Safety standards are paramount.", "metadata": {}}
        ]
        
        # setup llm mock
        mock_llm_instance = MagicMock()
        mock_get_llm.return_value = mock_llm_instance
        
        # create a mock stream
        mock_chunk1 = MagicMock()
        mock_chunk1.choices[0].delta.content = "The "
        mock_chunk2 = MagicMock()
        mock_chunk2.choices[0].delta.content = "EPA "
        mock_chunk3 = MagicMock()
        mock_chunk3.choices[0].delta.content = "regulates."
        
        # setup mock return for chat_completion
        async def async_stream():
            yield mock_chunk1
            yield mock_chunk2
            yield mock_chunk3
            
        async def mock_chat_completion_func(*args, **kwargs):
            if kwargs.get("use_case") == "router":
                # router expects a dict-like response
                return {"content": "core"}
            
            # rag expects a stream
            return async_stream()
            
        mock_llm_instance.chat_completion.side_effect = mock_chat_completion_func
        
        # execute
        generator = query_rag_sync("What does EPA regulate?")
        
        # consume generator
        chunks = list(generator)
        
        # verify structure
        # first chunk should be sources
        assert chunks[0]["type"] == "sources"
        assert len(chunks[0]["data"]) == 2
        
        # subsequent chunks are content
        content_text = "".join([c["delta"] for c in chunks if c["type"] == "content"])
        assert "The EPA regulates." in content_text
        mock_retrieval.assert_called_once()
        assert mock_llm_instance.chat_completion.call_count >= 1
