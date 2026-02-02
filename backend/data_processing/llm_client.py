"""
LLM client wrapper - now uses unified LLMProvider.
Kept for backward compatibility with data processing scripts.
"""

import logging
from shared.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Backward-compatible wrapper around unified LLMProvider.
    """
    
    def __init__(self):
        self.provider = LLMProvider()
    
    def validate_openai(self, model: str = "gpt-4o-mini") -> bool:
        """Check if OpenAI provider is available."""
        return "openai" in self.provider.clients or "openrouter" in self.provider.clients
    
    def validate_gemini(self) -> bool:
        """Check if Google provider is available."""
        return "google" in self.provider.clients
    
    async def chat_completion(self, messages, use_case="summarization", **kwargs):
        """Unified chat completion - delegates to LLMProvider."""
        return await self.provider.chat_completion(
            messages=messages,
            use_case=use_case,
            **kwargs
        )
    
    async def embed(self, texts, use_case="embeddings"):
        """Unified embeddings - delegates to LLMProvider."""
        return await self.provider.embed(texts, use_case=use_case)
