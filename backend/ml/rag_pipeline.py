"""langchain rag pipeline"""

from typing import Generator


def query_rag(question: str) -> Generator[str, None, None]:
    """
    query the rag pipeline with a question
    
    this is the main function that full-stack will call
    
    args:
        question: user question
        
    yields:
        answer chunks for streaming
    """
    # TODO: implement rag pipeline
    # 1. embed the question
    # 2. retrieve top-k chunks from chromadb
    # 3. build context from chunks
    # 4. generate answer using openrouter llm
    # 5. stream response
    yield "not implemented yet"
