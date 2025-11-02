"""
OpenAI Adapter Service

Wrapper around AsyncOpenAI client with token logging hooks and retry logic.
Provides consistent interface for all LLM operations across the application.

Reference: Section 1.2.1 - OpenAI Integration Foundation
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion


logger = logging.getLogger(__name__)


class OpenAIAdapter:
    """
    Adapter for OpenAI API with token logging and error handling.
    
    Features:
    - Async chat completions
    - Text embeddings
    - Token usage logging
    - Automatic retry with exponential backoff
    - Error handling and timeout management
    
    Example:
        adapter = OpenAIAdapter(api_key=os.getenv("OPENAI_API_KEY"))
        response = await adapter.chat_completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7
        )
    """
    
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    
    def __init__(self, api_key: str, token_logger: Optional[Any] = None):
        """
        Initialize OpenAI adapter.
        
        Args:
            api_key: OpenAI API key
            token_logger: Optional token logger instance with log_tokens() method
        """
        self.api_key = api_key
        self.token_logger = token_logger
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI adapter initialized")
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        **kwargs
    ) -> ChatCompletion:
        """
        Call OpenAI chat completion API with retry logic.
        
        Args:
            model: Model name (e.g., "gpt-4o-mini", "gpt-4o")
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional parameters (max_tokens, top_p, etc.)
        
        Returns:
            ChatCompletion response from OpenAI
        
        Raises:
            Exception: After MAX_RETRIES failed attempts
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"Chat completion attempt {attempt + 1}/{self.MAX_RETRIES}")
                
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    **kwargs
                )
                
                # Log tokens if logger provided
                self._log_tokens(response, kwargs)
                
                logger.info(
                    f"Chat completion successful: model={model}, "
                    f"tokens={response.usage.total_tokens if response.usage else 'N/A'}"
                )
                
                return response
                
            except Exception as e:
                logger.error(f"Chat completion attempt {attempt + 1} failed: {e}")
                
                if attempt < self.MAX_RETRIES - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = self.BASE_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Chat completion failed after {self.MAX_RETRIES} attempts")
                    raise
    
    async def embed_text(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> List[float]:
        """
        Generate text embeddings using OpenAI API.
        
        Args:
            text: Text to embed
            model: Embedding model name (default: text-embedding-3-small)
        
        Returns:
            List of float values representing the embedding vector
        """
        logger.debug(f"Generating embedding for text (length={len(text)})")
        
        response = await self.client.embeddings.create(
            model=model,
            input=text
        )
        
        embedding = response.data[0].embedding
        
        logger.info(f"Embedding generated: model={model}, dimensions={len(embedding)}")
        
        return embedding
    
    def _log_tokens(self, response: ChatCompletion, metadata: Dict[str, Any]) -> None:
        """
        Log token usage to token logger if configured.
        
        Args:
            response: ChatCompletion response with usage data
            metadata: Additional metadata to log (agent_id, project_id, etc.)
        """
        if self.token_logger is None:
            return
        
        if response.usage is None:
            logger.warning("Response has no usage data, skipping token logging")
            return
        
        try:
            self.token_logger.log_tokens(
                model=response.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                **metadata
            )
            logger.debug(
                f"Tokens logged: prompt={response.usage.prompt_tokens}, "
                f"completion={response.usage.completion_tokens}"
            )
        except Exception as e:
            logger.error(f"Failed to log tokens: {e}")
            # Don't fail the request if logging fails
