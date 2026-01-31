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
    "gemini-2.5-flash-lite": {"input": 0.0, "output": 0.0},  # Free tier
    "gpt-5-mini": {"input": 0.25, "output": 2.0},
    "gpt-5.2": {"input": 0.25, "output": 2.0},
    "default": {"input": 0.25, "output": 2.0}
}


class LLMClient:
    """
    Unified LLM client with OpenAI primary and Gemini fallback.
    """
    
    def __init__(self):
        # Clients (lazily initialized)
        self._openai_client = None
        self._openai_async_client = None
        self._gemini_model = None
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
        # Selected provider (after validation)
        self.selected_provider: Optional[str] = None  # "openai" or "gemini"
    
    def _init_openai(self):
        """Lazy initialize OpenAI."""
        if self._openai_client is None and self.openai_api_key:
            self._openai_client = OpenAI(api_key=self.openai_api_key)
        return self._openai_client

    def _init_openai_async(self):
        """Lazy initialize OpenAI async."""
        if self._openai_async_client is None and self.openai_api_key:
            self._openai_async_client = AsyncOpenAI(api_key=self.openai_api_key)
        return self._openai_async_client
    
    def _init_gemini(self):
        """Lazy initialize Gemini."""
        if self._gemini_model is None and self.google_api_key:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=self.google_api_key)
                self._gemini_model = client
                logger.info("Gemini fallback initialized")
            except ImportError:
                logger.warning("google-genai not installed, Gemini unavailable")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
        return self._gemini_model

    def validate_openai(self, model: str = "gpt-5-mini") -> bool:
        """
        Validate OpenAI key and quota by doing a minimal test call.
        Returns True if working, False otherwise.
        """
        client = self._init_openai()
        if not client:
            return False
            
        try:
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"OpenAI validation failed: {e}")
            return False

    def validate_gemini(self) -> bool:
        """
        Validate Gemini key and quota by doing a minimal test call.
        Returns True if working, False otherwise.
        """
        client = self._init_gemini()
        if not client:
            return False
            
        try:
            client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents="hi",
                config={"max_output_tokens": 1}
            )
            return True
        except Exception as e:
            logger.warning(f"Gemini validation failed: {e}")
            return False
    
    def select_best_provider(self) -> Optional[str]:
        """
        Proactively check providers and lock onto the first working one.
        Returns the name of the selected provider, or None if all fail.
        """
        # 1. Try OpenAI
        if self.validate_openai():
            self.selected_provider = "openai"
            logger.info("Validated OpenAI API. Locking to 'openai' provider.")
            return "openai"
            
        logger.warning("OpenAI validation failed or key missing.")
        
        # 2. Try Gemini
        if self.validate_gemini():
            self.selected_provider = "gemini"
            logger.info("Validated Gemini API. Locking to 'gemini' provider.")
            return "gemini"
            
        logger.warning("Gemini validation failed or key missing.")
        
        self.selected_provider = None
        return None  # No working provider

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Any] = None,
        **kwargs
    ):
        """
        Chat completion using the LOCKED provider (or fallback logic if not locked).
        """
        # If locked to a provider, use it exclusively
        if self.selected_provider == "gemini":
            return self._gemini_fallback(model, messages, response_format, **kwargs)
        elif self.selected_provider == "openai":
            # Proceed with OpenAI logic below
            pass
        elif self.selected_provider is None:
            # If explicit None was set (all failed), raise immediately
            # If never initialized (legacy usage), try default failover logic
            pass

        # Try OpenAI first
        client = self._init_openai()
        try:
            if not client:
                raise Exception("OpenAI API key missing")

            if response_format:
                response = client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    **kwargs
                )
            else:
                response = client.chat.completions.create(
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
            
            # Fallback to Gemini ONLY if not locked to OpenAI
            if self.selected_provider == "openai":
                logger.error(f"OpenAI failed while locked: {e}")
                raise e
                
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
        Async chat completion using the LOCKED provider.
        """
        # If locked to a provider, use it exclusively
        if self.selected_provider == "gemini":
            # Note: _gemini_fallback is currently synchronous, but we can wrap it or just use it (it blocks loop briefly)
            # For true async: would need async gemini client or threadpool
            # For now, just call it directly as it's a fallback/secondary
            return self._gemini_fallback(model, messages, response_format, **kwargs)
        
        # OpenAI Logic
        client = self._init_openai_async()
        try:
            if not client:
                raise Exception("OpenAI API key missing")

            if response_format:
                response = await client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    **kwargs
                )
            else:
                response = await client.chat.completions.create(
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
            if self.selected_provider == "openai":
                logger.error(f"OpenAI async failed while locked: {e}")
                raise e
                
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
        client = self._init_gemini()
        if not client:
            raise Exception("Gemini fallback unavailable and OpenAI failed")
        
        # Use correct Gemini model name
        gemini_model_name = "gemini-2.5-flash-lite"
        
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
            # Get schema from Pydantic model
            schema = response_format.model_json_schema()
            schema_str = json.dumps(schema, indent=2)
            prompt += f"\n\nRespond with a valid JSON object matching this schema:\n{schema_str}\n\nIMPORTANT: Return ONLY the JSON object with the data. Do NOT return the schema definition."
        
        # Call Gemini with new API
        response = client.models.generate_content(
            model=gemini_model_name,
            contents=prompt
        )
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
                cleaned_content = content
                if cleaned_content.startswith("```"):
                    cleaned_content = cleaned_content.split("```")[1]
                    if cleaned_content.startswith("json"):
                        cleaned_content = cleaned_content[4:]
                    cleaned_content = cleaned_content.strip()
                
                # Remove any trailing markdown blocks
                if "```" in cleaned_content:
                    cleaned_content = cleaned_content.split("```")[0].strip()
                
                # Fix common escape character issues in Gemini responses
                # Replace invalid escape sequences with valid ones
                import re
                # Fix unescaped backslashes before certain characters
                cleaned_content = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', cleaned_content)
                
                data = json.loads(cleaned_content)
                parsed = response_format.model_validate(data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini JSON response: {e}")
                logger.debug(f"Problematic content around error: {content[max(0, e.pos-100):e.pos+100]}")
                # Try one more time with aggressive cleaning
                try:
                    # Replace all backslashes with double backslashes, then fix valid escape sequences
                    aggressive_clean = cleaned_content.replace('\\', '\\\\')
                    aggressive_clean = aggressive_clean.replace('\\\\n', '\\n')
                    aggressive_clean = aggressive_clean.replace('\\\\t', '\\t')
                    aggressive_clean = aggressive_clean.replace('\\\\r', '\\r')
                    aggressive_clean = aggressive_clean.replace('\\\\"', '\\"')
                    aggressive_clean = aggressive_clean.replace('\\\\/', '\\/')
                    aggressive_clean = aggressive_clean.replace('\\\\\\\\', '\\\\')
                    
                    data = json.loads(aggressive_clean)
                    parsed = response_format.model_validate(data)
                    logger.info("Successfully parsed after aggressive cleaning")
                except Exception as retry_error:
                    logger.error(f"Aggressive cleaning also failed: {retry_error}")
                    raise e  # Raise original error
            except Exception as e:
                logger.error(f"Failed to validate Gemini response: {e}")
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
