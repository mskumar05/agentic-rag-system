"""
LLM integration supporting Ollama (local), Groq, and Together AI
"""
from typing import List, Dict, Optional
import logging
import json
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM service supporting multiple providers (Ollama, Groq, Together AI)
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        api_key: str = None
    ):
        """
        Initialize LLM service

        Args:
            provider: LLM provider ('ollama', 'groq', or 'together')
            model: Model name
            api_key: API key (not needed for Ollama)
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL

        # Initialize client based on provider
        if self.provider == "ollama":
            self.base_url = settings.OLLAMA_BASE_URL
            logger.info(f"Initialized Ollama client with model: {self.model}")
            logger.info(f"Ollama URL: {self.base_url}")
        elif self.provider == "groq":
            from groq import Groq
            self.api_key = api_key or settings.GROQ_API_KEY
            self.client = Groq(api_key=self.api_key)
            logger.info(f"Initialized Groq client with model: {self.model}")
        elif self.provider == "together":
            raise NotImplementedError("Together AI integration coming soon")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate(
        self,
        prompt: str,
        system_message: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> str:
        """
        Generate text completion

        Args:
            prompt: User prompt
            system_message: System message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated text
        """
        temperature = temperature or settings.LLM_TEMPERATURE
        max_tokens = max_tokens or settings.MAX_TOKENS

        try:
            if self.provider == "ollama":
                return self._generate_ollama(
                    prompt=prompt,
                    system_message=system_message,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            elif self.provider == "groq":
                return self._generate_groq(
                    prompt=prompt,
                    system_message=system_message,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                raise NotImplementedError(f"Provider {self.provider} not implemented")

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise

    def _generate_ollama(
        self,
        prompt: str,
        system_message: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Generate using Ollama local API"""

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_message or "",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama. Make sure Ollama is running!")
            logger.error("Start Ollama with: ollama serve")
            raise
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise

    def _generate_groq(
        self,
        prompt: str,
        system_message: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Generate using Groq API"""

        messages = []

        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return response.choices[0].message.content

    def generate_with_context(
        self,
        query: str,
        context_chunks: List[str],
        system_message: str = None,
        temperature: float = None
    ) -> str:
        """
        Generate response with retrieved context

        Args:
            query: User query
            context_chunks: Retrieved context chunks
            system_message: System message
            temperature: Sampling temperature

        Returns:
            Generated response
        """
        # Build context
        context = "\n\n".join([
            f"[{i+1}] {chunk}"
            for i, chunk in enumerate(context_chunks)
        ])

        # Build prompt
        prompt = f"""Based on the following context, answer the user's question.

Context:
{context}

Question: {query}

Answer:"""

        return self.generate(
            prompt=prompt,
            system_message=system_message,
            temperature=temperature
        )

    def generate_structured(
        self,
        prompt: str,
        response_format: Dict,
        system_message: str = None,
        temperature: float = 0.1
    ) -> Dict:
        """
        Generate structured JSON output

        Args:
            prompt: User prompt
            response_format: Expected JSON schema
            system_message: System message
            temperature: Low temperature for structured output

        Returns:
            Parsed JSON response
        """
        system_msg = system_message or "You are a helpful assistant that outputs JSON."

        # Add JSON instruction to prompt
        json_prompt = f"""{prompt}

Please respond with a valid JSON object following this format:
{json.dumps(response_format, indent=2)}"""

        response = self.generate(
            prompt=json_prompt,
            system_message=system_msg,
            temperature=temperature
        )

        # Parse JSON
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response}")
            raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Chat completion with message history

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Assistant response
        """
        temperature = temperature or settings.LLM_TEMPERATURE
        max_tokens = max_tokens or settings.MAX_TOKENS

        try:
            if self.provider == "ollama":
                # For Ollama, use chat API
                url = f"{self.base_url}/api/chat"

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }

                response = requests.post(url, json=payload, timeout=120)
                response.raise_for_status()

                result = response.json()
                return result.get("message", {}).get("content", "")

            elif self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            else:
                raise NotImplementedError(f"Provider {self.provider} not implemented")

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise


# Singleton instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
