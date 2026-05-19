"""Re-export for tests (implementation lives in src.rag.deterministic_embeddings)."""
from src.rag.deterministic_embeddings import DeterministicEmbeddings as FakeEmbeddings

__all__ = ["FakeEmbeddings"]
