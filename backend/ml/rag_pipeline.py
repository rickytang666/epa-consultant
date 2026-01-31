"""rag pipeline"""

import os
from typing import AsyncGenerator, Any
from openai import AsyncOpenAI
from google import genai
from google import genai
from ml.retrieval import retrieve_relevant_chunks
from ml.judge import JudgeAgent
from ml.hallucination import HallucinationDetector

# config
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# clients
# use openai client for openrouter
or_client = None
if OPENROUTER_API_KEY:
    or_client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

google_client = None
if GOOGLE_API_KEY:
    google_client = genai.Client(api_key=GOOGLE_API_KEY)

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
    chunks = retrieve_relevant_chunks(query, n_results=top_k)
    
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
    
    # 4. generate answer (streaming)
    # try openrouter first
    if or_client:
        try:
            stream = await or_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True
            )
            async for chunk in stream:
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
            # Google GenAI python SDK might not support async streaming natively in this version easily?
            # Actually checking docs, genai.Client is sync? 
            # We will wrap it or keep it sync but yield async?
            # Ideally we use google-generativeai async client but let's stick to simple implementation.
            # Since we focused on OpenRouter mostly, we can keep this part semi-sync or refactor later.
            # But let's assume OpenRouter is primary.
            
            response = google_client.models.generate_content(
                model="gemini-2.5-flash-lite", 
                contents=full_prompt,
                config=None
            )
            # simulate streaming for now - this part blocks, but it's a fallback.
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


def _generate_standalone_query(query: str, chat_history: list[dict[str, str]], client: OpenAI) -> str:
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
        response = client.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, # low temp for precision
            max_tokens=100
        )
        rewritten = response.choices[0].message.content.strip()
        # fallback if model fails or returns empty
        return rewritten if rewritten else query
    except Exception:
        # fallback to original query if rewrite fails
        return query


def query_rag(query: str, chat_history: list[dict[str, str]] = None, top_k: int = 10) -> Generator[dict[str, Any], None, None]:
    """
    answer a query using rag with conversation memory
    
    args:
        query: user question
        chat_history: list of {"role": "user"|"assistant", "content": "..."}
        top_k: number of chunks to retrieve (default 10)
        
    yields:
        chunks of the answer (streaming)
    """
    if not query:
        yield {"type": "content", "delta": ""}
        return

    # 1. contextualize query (memory)
    search_query = query
    if chat_history and or_client:
        search_query = _generate_standalone_query(query, chat_history, or_client)
        # print(f"Rewritten Query: {search_query}") 

    # 2. retrieve context using standalone query
    # optimize: reduce k to 3 for speed/cost, usually sufficient for RAG
    chunks = retrieve_relevant_chunks(search_query, n_results=top_k)
    
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

    # 3. yield sources event immediately
    yield {
        "type": "sources",
        "data": chunks  # List of dicts with file, page, text, etc.
    }

    # 4. construct prompt
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
        "Format your response in Markdown. Be extremely concise and professional. Do not chat or 'yap'—get straight to the answer. "
        "Answer the question directly—avoid including information not asked for. "
        "When referencing specific rules or sections, cite the source using the format [Source: Header > Path]. "
        "CRITICAL: Pay close attention to exceptions, conditions, and qualifiers (e.g., 'unless', 'except', 'provided that'). "
        "If a rule has exceptions, explicitly state them. Do not give a flat 'Yes' or 'No' if the answer is conditional. "
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
    
    # use original query in prompt, but standalone drove retrieval
    user_prompt = f"Context:\n{context_text}\n\nQuestion: {query}"
    
    if chat_history:
        # optionally append recent history to prompt so model knows flow
        # simpler to just let it answer the specific question given context
        pass


    # 5. generate answer with adaptive loop
    
    # helper to generate text (non-streaming) for the judge
    def generate_full_answer(s_prompt, u_prompt, model_name="openai/gpt-oss-120b"):
        if or_client:
            try:
                resp = or_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": s_prompt}, {"role": "user", "content": u_prompt}]
                )
                return resp.choices[0].message.content
            except:
                return None
        return None

    # initial attempt
    initial_answer = None
    if or_client:
        # yield status
        yield {"type": "content", "delta": "**Structuring answer...**\n\n"}
        
        initial_answer = generate_full_answer(system_prompt, user_prompt)
        
        if initial_answer:
            # judge it
            judge = JudgeAgent(or_client)
            evaluation = judge.evaluate_answer(search_query, context_text, initial_answer)
            
            # helpful debug info for user
            # yield {"type": "content", "delta": f"*(Confidence: {evaluation['score']:.2f})*\n\n"}
            
            if evaluation["needs_refinement"]:
                # yield {"type": "content", "delta": "*(Verifying information...)*\n\n"}
                
                # adaptive step: refine query
                refined_query = judge.suggest_refined_query(search_query, evaluation["reason"])
                
                # simple re-retrieval (could be recursive, but 1-hop is usually enough)
                new_chunks = retrieve_relevant_chunks(refined_query, n_results=top_k)
                
                # rebuild context with new chunks (merging or replacing)
                # for simplicity, let's just append new unique chunks
                existing_ids = {c["chunk_id"] for c in chunks}
                for nc in new_chunks:
                    if nc["chunk_id"] not in existing_ids:
                        truncated_chunks.append(nc) # add to context list
                
                # rebuild prompt context
                context_parts = [] # reset
                for c in truncated_chunks:
                    meta = c.get("metadata", {})
                    part = ""
                    if "header_path_str" in meta:
                        part += f"[Source: {meta['header_path_str']}]\n"
                    part += f"{c['text']}"
                    context_parts.append(part)
                context_text = "\n\n---\n\n".join(context_parts)
                user_prompt = f"Context:\n{context_text}\n\nQuestion: {query}"
                
                # re-generate final answer
    
    # final streaming generation
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
            yield {"type": "clear", "delta": ""} # special signal to clear "thinking" text if UI supports it
            
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield {
                        "type": "content", 
                        "delta": content
                    }
                    
            # append confidence score if available
            if initial_answer and evaluation:
                # optional: run programmatic verification
                verification_score = 0.0
                try:
                    verifier = HallucinationDetector.get_instance() # this uses the singleton instance
                    verification_score = verifier.compute_score(context_text, initial_answer)
                except Exception as e:
                    print(f"verifier error: {e}")

                yield {
                    "type": "content", 
                    "delta": f"\n\n---\n**Confidence Score**: {evaluation['score']:.2f}/1.0\n**Fact Check Score**: {verification_score:.2f}/1.0"
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
