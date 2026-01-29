"""rag pipeline"""

import os
from typing import Generator, Any
from openai import OpenAI
from google import genai
from ml.retrieval import retrieve_relevant_chunks

# config
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# clients
# use openai client for openrouter
or_client = None
if OPENROUTER_API_KEY:
    or_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

google_client = None
if GOOGLE_API_KEY:
    google_client = genai.Client(api_key=GOOGLE_API_KEY)

def query_rag(query: str) -> Generator[dict[str, Any], None, None]:
    """
    answer a query using rag
    
    args:
        query: user question
        
    yields:
        chunks of the answer (streaming)
    """
    if not query:
        yield {"type": "content", "delta": ""}
        return

    # 1. retrieve context
    chunks = retrieve_relevant_chunks(query, n_results=5)
    context_text = "\n\n".join([c["text"] for c in chunks])
    
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
    for c in chunks:
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
    
    # 4. generate answer (streaming)
    # try openrouter first
    if or_client:
        try:
            stream = or_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield {
                        "type": "content", 
                        "delta": content
                    }
            return
        except Exception:
            pass # fallback
            
    # fallback to google gemini
    if google_client:
        try:
            # gemini streaming
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = google_client.models.generate_content(
                model="gemini-2.5-flash-lite", 
                contents=full_prompt,
                config=None
            )
            # simulate streaming for now
            if hasattr(response, 'text') and response.text:
                yield {
                    "type": "content", 
                    "delta": response.text
                }
                return
        except Exception as e:
            yield {
                "type": "content", 
                "delta": f"Error generating response: {e}"
            }
            return
            
    if not or_client and not google_client:
        yield {
            "type": "content", 
            "delta": "Configuration Error: No API keys found (OpenRouter or Google)."
        }
