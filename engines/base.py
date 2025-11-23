# engines/base.py
class BaseEngine:
    """Abstract base class for all external AI engines."""

    def __init__(self, name: str, api_key: str = None):
        self.name = name
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        """Override in subclasses"""
        raise NotImplementedError
