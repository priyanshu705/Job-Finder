// src/finder/core/ai/base_provider.py
"""Abstract base class for AI providers.
All providers must implement a `generate` method returning the raw response string.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response for the given prompt.
        Implementations should handle retries, timeouts, and any
        provider‑specific logic.
        """
        raise NotImplementedError
