"""Router module for intent classification.

Contains implementations of different routing strategies:
- RuleBasedRouter (V1): Deterministic keyword-based routing
- LLMRouter (V2): Optional LLM-based intent classification
- AdaptiveRouter (V3): Deterministic routing with an optional LLM fallback
"""
