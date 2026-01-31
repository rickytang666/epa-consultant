"""
Unified LLM provider with smart fallback chains.
Supports OpenRouter, OpenAI, and Google with automatic provider detection.
"""

import os
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator, Union
from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger(__name__)

# Lazy import for Google
_genai = None

def _get_genai():
    global _genai
    if _genai is None:
        try:
            from google import genai
            _genai = genai
        except ImportError:
            logger.warning("Google genai not installed")
    return _genai


class LLMProvider:
    """
    Unified LLM provider with automatic fallback chains.
    
    Supports 3 providers with 2-level fallbacks for each use case:
    - OpenRouter (meta-llama, gpt-oss models)
    - OpenAI (gpt-4o-mini, gpt-5-mini, embeddings)
    - Google (gemini models, embeddings)
    """
    
    # Fallback chains: (provider, model) tuples in priority order
    FALLBACK_CHAINS = {
        "query_enrichment": [
            ("openrouter", "meta-llama/llama-3-8b-instruct"),
            ("openai", "gpt-4o-mini"),
            ("google", "gemini-2.0-flash")
        ],
        "rag_generation": [
            ("openrouter", "openai/gpt-oss-120b"),
            ("openai", "gpt-4o-mini"),
            ("google", "gemini-2.0-flash")
        ],
        "embeddings": [
            ("openai", "text-embedding-3-small"),
            ("google", "text-embedding-004")
        ],
        "summarization": [
            ("openai", "gpt-5-mini"),
            ("openrouter", "meta-llama/llama-3-8b-instruct"),
            ("google", "gemini-2.5-flash-lite")
        ]
    }
    
    def __init__(self):
        self.clients: Dict[str, Any] = {}
        self._init_clients()
    
    def _init_clients(self):
        """Initialize all available providers."""
        # OpenRouter
        if os.getenv("OPENROUTER_API_KEY"):
            self.clients["openrouter"] = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )
            logger.info("✓ OpenRouter client initialized")
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            self.clients["openai"] = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
            logger.info("✓ OpenAI client initialized")
        
        # Google
        if os.getenv("GOOGLE_API_KEY"):
            genai = _get_genai()
            if genai:
                self.clients["google"] = genai.Client(
                    api_key=os.getenv("GOOGLE_API_KEY")
                )
                logger.info("✓ Google client initialized")
        
        if not self.clients:
            raise ValueError("No LLM providers available. Set OPENROUTER_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY")
        
        logger.info(f"Available providers: {list(self.clients.keys())}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        use_case: str,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[AsyncGenerator, Dict[str, Any]]:
        """
        Unified chat completion with automatic fallback.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            use_case: One of: query_enrichment, rag_generation, summarization
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional provider-specific args
        
        Returns:
            AsyncGenerator if stream=True, else dict with response
        """
        chain = self.FALLBACK_CHAINS.get(use_case)
        if not chain:
            raise ValueError(f"Unknown use_case: {use_case}")
        
        last_error = None
        for provider_name, model_name in chain:
            if provider_name not in self.clients:
                continue
            
            try:
                logger.debug(f"Trying {provider_name}/{model_name} for {use_case}")
                return await self._call_provider(
                    provider_name,
                    model_name,
                    messages,
                    stream,
                    temperature,
                    max_tokens,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"{provider_name} failed for {use_case}: {e}")
                last_error = e
                continue
        
        raise Exception(f"All providers failed for {use_case}. Last error: {last_error}")
    
    async def _call_provider(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ):
        """Call specific provider with unified interface."""
        if provider in ["openrouter", "openai"]:
            return await self._openai_style_call(
                self.clients[provider],
                model,
                messages,
                stream,
                temperature,
                max_tokens,
                **kwargs
            )
        elif provider == "google":
            return await self._google_call(
                model,
                messages,
                stream,
                temperature,
                max_tokens,
                **kwargs
            )
    
    async def _openai_style_call(
        self,
        client: AsyncOpenAI,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ):
        """OpenAI-compatible API call."""
        params = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        params.update(kwargs)
        
        response = await client.chat.completions.create(**params)
        
        if stream:
            return response  # Return async generator directly
        else:
            return {
                "content": response.choices[0].message.content,
                "model": model
            }
    
    async def _google_call(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ):
        """Google Gemini API call (non-blocking wrapper)."""
        import asyncio
        
        # Convert messages to Google format
        prompt = self._messages_to_google_prompt(messages)
        
        config = {
            "temperature": temperature,
        }
        if max_tokens:
            config["max_output_tokens"] = max_tokens
        
        client = self.clients["google"]
        
        if stream:
            # Google streaming - wrap in async generator
            async def google_stream_wrapper():
                # Run sync streaming call in a thread to get the iterator
                response = await asyncio.to_thread(
                    client.models.generate_content_stream,
                    model=model,
                    contents=prompt,
                    config=config
                )
                
                # Iterate over the sync response in a thread to avoid blocking
                def get_next_chunk(it):
                    try:
                        return next(it)
                    except StopIteration:
                        return None

                while True:
                    chunk = await asyncio.to_thread(get_next_chunk, response)
                    if chunk is None:
                        break
                    if chunk.text:
                        # Mimic OpenAI chunk structure
                        yield type('Chunk', (), {
                            'choices': [type('Choice', (), {
                                'delta': type('Delta', (), {'content': chunk.text})()
                            })()]
                        })()
            
            return google_stream_wrapper()
        else:
            # Run sync call in a thread to avoid blocking event loop
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=config
            )
            return {
                "content": response.text,
                "model": model
            }

    def _messages_to_google_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style messages to Google prompt format."""
        # More structured conversion for Gemini
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"INSTRUCTIONS:\n{content}")
            elif role == "user":
                parts.append(f"USER:\n{content}")
            elif role == "assistant":
                parts.append(f"ASSISTANT:\n{content}")
        return "\n\n---\n\n".join(parts)
    
    async def embed(
        self,
        texts: Union[str, List[str]],
        use_case: str = "embeddings"
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings with automatic fallback.
        
        Args:
            texts: Single text or list of texts
            use_case: Use case for fallback chain selection
        
        Returns:
            Single embedding vector or list of vectors
        """
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]
        
        chain = self.FALLBACK_CHAINS.get(use_case, self.FALLBACK_CHAINS["embeddings"])
        
        last_error = None
        for provider_name, model_name in chain:
            if provider_name not in self.clients:
                continue
            
            try:
                logger.debug(f"Trying {provider_name}/{model_name} for embeddings")
                embeddings = await self._embed_provider(provider_name, model_name, texts)
                return embeddings[0] if is_single else embeddings
            except Exception as e:
                logger.warning(f"{provider_name} embeddings failed: {e}")
                last_error = e
                continue
        
        raise Exception(f"All providers failed for embeddings. Last error: {last_error}")
    
    async def _embed_provider(
        self,
        provider: str,
        model: str,
        texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings from specific provider."""
        if provider == "openai":
            client = self.clients["openai"]
            response = await client.embeddings.create(
                input=texts,
                model=model
            )
            return [item.embedding for item in response.data]
        
        elif provider == "google":
            import asyncio
            client = self.clients["google"]
            # Google embeddings are sync, wrap in thread
            result = await asyncio.to_thread(
                client.models.embed_content,
                model=model,
                contents=texts
            )
            return result.embeddings
        
        else:
            raise ValueError(f"Embeddings not supported for provider: {provider}")
