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


async def query_rag(
    query: str, chat_history: list[dict[str, str]] = None, top_k: int = 10
) -> AsyncGenerator[dict[str, Any], None]:
    """
    answer a query using rag with intent routing and memory
    """
    if not query:
        yield {"type": "content", "delta": ""}
        return

    # 1. router: usage cheap model to classify intent
    # bypass rag for chitchat/greetings
    intent = await classify_intent(query)

    if intent == "supplemental":
        yield {"type": "content", "delta": ""}  # init stream
        try:
            stream = await _get_llm().chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful EPA Consultant assistant. Respond politely to the user's greeting or comment. Be concise.",
                    },
                    {"role": "user", "content": query},
                ],
                use_case="router",
                stream=True,
            )
            async for chunk in stream:
                content = (
                    chunk.choices[0].delta.content
                    if chunk.choices[0].delta.content
                    else ""
                )
                if content:
                    yield {"type": "content", "delta": content}
            return
        except Exception as e:
            yield {
                "type": "content",
                "delta": "Hello! How can I help you with EPA regulations today?",
            }
            return

    # 2. contextualize
    # rewrite query if history exists
    search_query = query
    if chat_history:
        search_query = await _generate_standalone_query(query, chat_history)

    # 3. retrieve context
    chunks = await retrieve_relevant_chunks(search_query, n_results=top_k)

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

    # 4. Yield Sources Event immediately
    yield {
        "type": "sources",
        "data": chunks,  # List of dicts with file, page, text, etc.
    }

    # 5. construct prompt
    # extract document summary from first chunk if available
    doc_summary = ""
    for c in chunks:
        if c.get("metadata", {}).get("document_summary"):
            doc_summary = c["metadata"]["document_summary"]
            break

    system_prompt = (
        "You are an expert EPA consultant. Answer the user's question clearly and accurately using ONLY the provided context.\n\n"
        "GUIDELINES:\n"
        "1. **Professional & Concise**: Answer directly and professionally. Avoid fluff, but ensure the answer is complete.\n"
        "2. **Formatting**: Use Markdown for readability. **Format lists of data, deadlines, or comparisons as Markdown Tables**.\n"
        "3. **Accuracy**: Use exact dates, numbers, and definitions from the text.\n"
        "4. **No Hallucinations**: If the answer is not in the context, state 'I do not have enough information'.\n"
        "5. **Citations**: End with [Source: ...].\n"
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
                {"role": "user", "content": user_prompt},
            ],
            use_case="rag_generation",
            stream=True,
            temperature=0.0,
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
                yield {"type": "content", "delta": content}
        # print("DEBUG: stream completed")
    except Exception as e:
        yield {"type": "content", "delta": f"Error generating response: {e}"}


async def classify_intent(query: str) -> str:
    """
    Classify query intent: "supplemental" (chitchat) or "core" (needs rag)
    """
    messages = [
        {
            "role": "system",
            "content": "You are a query router. Classify the user query as either 'supplemental' (greetings, chitchat, compliments, generic pleasantries) or 'core' (needs information retrieval about EPA, permits, regulations). Return ONLY the label 'supplemental' or 'core'.",
        },
        {"role": "user", "content": query},
    ]
    try:
        response = await _get_llm().chat_completion(
            messages=messages,
            use_case="router",
            stream=False,
            max_tokens=10,
            temperature=0.0,
        )
        content = response.get("content", "").strip().lower()
        return "supplemental" if "supplemental" in content else "core"
    except Exception as e:
        print(f"Router failed: {e}")
        return "core"  # fallback to safe option


async def _generate_standalone_query(
    query: str, chat_history: list[dict[str, str]]
) -> str:
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

    user_prompt = (
        f"Chat History:\n{history_str}\nUser Question: {query}\n\nRewritten Question:"
    )

    try:
        response = await _get_llm().chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            use_case="query_enrichment",
            stream=False,
            temperature=0.1,
            max_tokens=100,
        )
        rewritten = response.get("content", "").strip()
        return rewritten if rewritten else query
    except Exception:
        # fallback to original query if rewrite fails
        return query


def query_rag_sync(
    query: str, chat_history: list[dict[str, str]] = None, top_k: int = 10
) -> Generator[dict[str, Any], None, None]:
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
