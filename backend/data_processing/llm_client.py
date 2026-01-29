"""
LLM client wrapper with OpenAI primary and Gemini fallback.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List

from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

# Pricing per 1M tokens
PRICING = {
    "gemini-2.0-flash-lite": {"input": 0.0, "output": 0.0},  # Free tier
    "gpt-5-mini": {"input": 0.25, "output": 2.0},
    "gpt-5.2": {"input": 0.25, "output": 2.0},
    "default": {"input": 0.25, "output": 2.0}
}


class LLMClient:
    """
    Unified LLM client with OpenAI primary and Gemini fallback.
    """
    
    def __init__(self):
        # OpenAI (primary)
        self.openai_client = OpenAI()
        self.openai_async_client = AsyncOpenAI()
        
        # Gemini (fallback) - lazy load
        self._gemini_model = None
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
    
    def _init_gemini(self):
        """Lazy initialize Gemini."""
        if self._gemini_model is None and self.google_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.google_api_key)
                self._gemini_model = genai
                logger.info("Gemini fallback initialized")
            except ImportError:
                logger.warning("google-generativeai not installed, Gemini unavailable")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
        return self._gemini_model
    
    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Any] = None,
        **kwargs
    ):
        """
        Chat completion with OpenAI primary, Gemini fallback.
        """
        # Try OpenAI first
        try:
            if response_format:
                response = self.openai_client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    **kwargs
                )
            else:
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
                )
            
            usage = response.usage
            pricing = PRICING.get(model, PRICING["default"])
            cost = (usage.prompt_tokens / 1_000_000) * pricing["input"] + \
                   (usage.completion_tokens / 1_000_000) * pricing["output"]
            
            logger.info(f"OpenAI {model} | Tokens: {usage.prompt_tokens} in, {usage.completion_tokens} out | Cost: ${cost:.6f}")
            
            # Return with cost attached
            return response, cost
            
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}, trying Gemini fallback...")
            
            # Fallback to Gemini
            return self._gemini_fallback(model, messages, response_format, **kwargs)
    
    async def async_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Any] = None,
        **kwargs
    ):
        """
        Async chat completion with OpenAI primary, Gemini fallback.
        """
        try:
            if response_format:
                response = await self.openai_async_client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    **kwargs
                )
            else:
                response = await self.openai_async_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
                )
            
            usage = response.usage
            pricing = PRICING.get(model, PRICING["default"])
            cost = (usage.prompt_tokens / 1_000_000) * pricing["input"] + \
                   (usage.completion_tokens / 1_000_000) * pricing["output"]
            
            logger.info(f"OpenAI {model} | Tokens: {usage.prompt_tokens} in, {usage.completion_tokens} out | Cost: ${cost:.6f}")
            
            return response, cost
            
        except Exception as e:
            logger.warning(f"OpenAI async failed: {e}, trying Gemini fallback...")
            return self._gemini_fallback(model, messages, response_format, **kwargs)
    
    def _gemini_fallback(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Any] = None,
        **kwargs
    ):
        """Fallback to Gemini."""
        genai = self._init_gemini()
        if not genai:
            raise Exception("Gemini fallback unavailable and OpenAI failed")
        
        # Map to Gemini model
        gemini_model_name = "gemini-2.0-flash-exp"  # Free tier
        
        # Build prompt
        prompt_parts = []
        for msg in messages:
            if msg["role"] == "system":
                prompt_parts.append(f"System: {msg['content']}\n")
            elif msg["role"] == "user":
                prompt_parts.append(msg["content"])
        
        prompt = "\n".join(prompt_parts)
        
        # Add JSON schema hint if structured output needed
        if response_format:
            prompt += "\n\nRespond in valid JSON format only, no markdown formatting."
        
        # Call Gemini
        model_instance = genai.GenerativeModel(gemini_model_name)
        response = model_instance.generate_content(prompt)
        content = response.text
        
        # Estimate tokens (Gemini doesn't provide exact counts)
        input_tokens = len(prompt.split()) * 1.3
        output_tokens = len(content.split()) * 1.3
        
        pricing = PRICING.get(gemini_model_name, PRICING["default"])
        cost = (input_tokens / 1_000_000) * pricing["input"] + \
               (output_tokens / 1_000_000) * pricing["output"]
        
        logger.info(f"Gemini {gemini_model_name} | Tokens: ~{int(input_tokens)} in, ~{int(output_tokens)} out | Cost: ${cost:.6f}")
        
        # Parse structured output if needed
        parsed = None
        if response_format:
            try:
                # Clean markdown code blocks if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                
                data = json.loads(content)
                parsed = response_format.model_validate(data)
            except Exception as e:
                logger.error(f"Failed to parse Gemini JSON response: {e}")
                raise
        
        # Return OpenAI-compatible format
        class MockUsage:
            def __init__(self, prompt_tokens, completion_tokens):
                self.prompt_tokens = prompt_tokens
                self.completion_tokens = completion_tokens
        
        class MockMessage:
            def __init__(self, content, parsed):
                self.content = content
                self.parsed = parsed
        
        class MockChoice:
            def __init__(self, message):
                self.message = message
        
        class MockResponse:
            def __init__(self, content, parsed, usage):
                self.choices = [MockChoice(MockMessage(content, parsed))]
                self.usage = usage
        
        mock_response = MockResponse(
            content,
            parsed,
            MockUsage(int(input_tokens), int(output_tokens))
        )
        
        return mock_response, cost
