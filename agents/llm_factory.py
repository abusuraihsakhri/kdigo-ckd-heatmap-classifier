"""Deterministic mock responder only; no external model provider is configured."""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name="Kdigo Ckd Heatmap Classifier"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return ("Mock mode only. No language model, guideline lookup, or clinical "
                "verification was performed. Use the KDIGO classification endpoint "
                "for deterministic GFR/albuminuria risk categories.")


class LLMFactory:
    @staticmethod
    def create(provider="mock", system_name="Kdigo Ckd Heatmap Classifier"):
        if str(provider).lower() not in ("mock", "deterministic", "test"):
            raise ValueError("Only the deterministic mock provider is implemented")
        return MockLLM(system_name)
