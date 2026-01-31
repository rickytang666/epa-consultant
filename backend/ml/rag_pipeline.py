"""rag pipeline"""

from typing import AsyncGenerator, Generator, Any
from ml.retrieval import retrieve_relevant_chunks
from shared.llm_provider import LLMProvider

# Lazy initialization
_llm_instance = None

def _get_llm():
    """Lazy-load LLM provider on first use."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMProvider()
    return _llm_instance

async def query_rag(query: str) -> AsyncGenerator[dict[str, Any], None]:
    """
    answer a query using rag
    
    args:
        query: user question
        top_k: number of chunks to retrieve (default 3)
        
    yields:
        chunks of the answer (streaming)
    """
    if not query:
        yield {"type": "content", "delta": ""}
        return

    print("query:", query)
    # 1. retrieve context
    # optimize: reduce k to 3 for speed/cost, usually sufficient for RAG
    chunks = await retrieve_relevant_chunks(query, n_results=3)
    
    # optimize: truncate duplicate or massive chunks to avoid token limit errors
    # average chunk is ~800 chars, but outliers can be 30k+
    MAX_CHUNK_CHARS = 4000 
    
    truncated_chunks = []
    for c in chunks:
        # shallow copy to avoid mutating original for sources
        c_copy = c.copy()
        if len(c_copy["text"]) > MAX_CHUNK_CHARS:
            c_copy["text"] = c_copy["text"][:MAX_CHUNK_CHARS] + "... [truncated]"
        truncated_chunks.append(c_copy)

    # 2. Yield Sources Event immediately
    yield {
        "type": "sources",
        "data": chunks  # List of dicts with file, page, text, etc.
    }

    # 3. construct prompt
    # extract document summary from first chunk if available
    doc_summary = ""
    for c in chunks:
        if c.get("metadata", {}).get("document_summary"):
            doc_summary = c["metadata"]["document_summary"]
            break
            
    system_prompt = (
        "You are an expert EPA consultant helper. "
        "Use the provided context to answer the user's question. "
        "Your answers must be grounded in the context. "
        "When referencing specific rules or sections, cite the source using the format [Source: Header > Path]. "
        "If the answer is not in the context, say you don't know.\n\n"
    )
    
    if doc_summary:
        system_prompt += f"Document Summary: {doc_summary}\n"

    # build context with section summaries
    context_parts = []
    for c in truncated_chunks:
        meta = c.get("metadata", {})
        part = ""
        # add header path for context
        if "header_path_str" in meta:
            part += f"[Source: {meta['header_path_str']}]\n"
        # add section summary
        if "section_summary" in meta:
            part += f"[Section Summary: {meta['section_summary']}]\n"
        
        part += f"{c['text']}"
        context_parts.append(part)

    context_text = "\n\n---\n\n".join(context_parts)
    
    user_prompt = f"Context:\n{context_text}\n\nQuestion: {query}"
    
    # 4. generate answer (streaming) using unified provider
    try:
        stream = await _get_llm().chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            use_case="rag_generation",
            stream=True
        )
        
        # print(f"DEBUG: stream initialized for rag_generation")
        async for chunk in stream:
            content = None
            try:
                content = chunk.choices[0].delta.content
            except (AttributeError, IndexError):
                # Handle different chunk structures if necessary
                pass
                
            if content:
                # print(f"DEBUG: yielding chunk: {content[:20]}...")
                yield {
                    "type": "content", 
                    "delta": content
                }
        # print("DEBUG: stream completed")
    except Exception as e:
        yield {
            "type": "content", 
            "delta": f"Error generating response: {e}"
        }



async def _generate_standalone_query(query: str, chat_history: list[dict[str, str]]) -> str:
    """
    rewrite query to be standalone based on history via llm
    """
    if not chat_history:
        return query

    # keep last 2 turns to save tokens
    recent_history = chat_history[-2:]
    
    history_str = ""
    for msg in recent_history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "")
        history_str += f"{role}: {content}\n"

    system_prompt = (
        "You are a query enrichment assistant. "
        "Rewrite the following user question to be a standalone, search-optimized question. "
        "1. Replace pronouns (it, they, this) with specific references from the history. "
        "2. Enrich the query with relevant context, specific keywords, or regulatory terms from the conversation to improve retrieval. "
        "Do NOT answer the question. Return ONLY the enriched question. "
        "If the question is already optimal, return it exactly as is."
    )
    
    user_prompt = f"Chat History:\n{history_str}\nUser Question: {query}\n\nRewritten Question:"

    try:
        response = await _get_llm().chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            use_case="query_enrichment",
            stream=False,
            temperature=0.1,
            max_tokens=100
        )
        rewritten = response.get("content", "").strip()
        return rewritten if rewritten else query
    except Exception:
        # fallback to original query if rewrite fails
        return query



def query_rag_sync(query: str, chat_history: list[dict[str, str]] = None, top_k: int = 10) -> Generator[dict[str, Any], None, None]:
    """
    Synchronous wrapper around async query_rag for backward compatibility.
    Used by test files and scripts.
    
    Note: This collects all async results then yields them synchronously.
    For production use, prefer the async query_rag directly.
    """
    import asyncio
    
    async def _collect_results():
        results = []
        async for chunk in query_rag(query):
            results.append(chunk)
        return results
    
    # Run async function and yield results
    results = asyncio.run(_collect_results())
    for chunk in results:
        yield chunk
