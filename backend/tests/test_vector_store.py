import os
import pytest
import chromadb
from ml.vector_store import init_vector_store, insert_chunks, CHROMA_DB_DIR

@pytest.fixture
def mock_chroma_dir():
    """fixture to create and teardown a temporary chroma dir logic if needed"""
    # reliant on main dir with separate test collection name for now
    pass

def test_init_vector_store():
    """test that we can initialize the store and get a collection"""
    collection = init_vector_store(collection_name="test_init")
    assert collection is not None
    assert collection.name == "test_init"

def test_insert_chunks():
    """test inserting chunks"""
    collection_name = "test_insert"
    
    # mock chunks
    chunks = [
        {
            "chunk_id": "test_1",
            "text": "hello world",
            "metadata": {"page": 1, "source": "test.pdf"}
        },
        {
            "chunk_id": "test_2",
            "text": "vector databases are cool",
            "metadata": {"page": 2, "source": "test.pdf"}
        }
    ]
    
    # mock embeddings (dim 768 for gemini)
    embeddings = [
        [0.1] * 768,
        [0.2] * 768
    ]
    
    insert_chunks(chunks, embeddings, collection_name=collection_name)
    
    # verify
    collection = init_vector_store(collection_name)
    assert collection.count() == 2
    
    # cleanup
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    client.delete_collection(collection_name)
