"""BGE-family embeddings via sentence-transformers (stable GPU on Windows)."""
from __future__ import annotations

import logging
import platform
from typing import List

from src.rag.bge_m3_embeddings import QUERY_PREFIX, DOC_PREFIX, resolve_torch_device

logger = logging.getLogger(__name__)

# BGE-M3 dense often crashes on Windows (native exit); BGE-large is same 1024-dim quality tier.
_WINDOWS_BGE_FALLBACK = "BAAI/bge-large-en-v1.5"


def effective_embedding_model(requested: str) -> str:
    """Pick a model that loads reliably on this host."""
    name = (requested or "BAAI/bge-m3").strip()
    if platform.system() == "Windows" and "bge-m3" in name.lower():
        if name.lower() != _WINDOWS_BGE_FALLBACK.lower():
            logger.info(
                "Windows: using %s on GPU instead of %s (BGE-M3 loader is unstable here)",
                _WINDOWS_BGE_FALLBACK,
                name,
            )
        return _WINDOWS_BGE_FALLBACK
    return name


class SentenceTransformerEmbeddings:
    """LangChain-compatible embeddings using sentence-transformers + PyTorch."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int = 16,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        resolved = effective_embedding_model(model_name or "BAAI/bge-m3")
        self.model_name = resolved
        self.device = resolve_torch_device(device)
        self.batch_size = batch_size
        logger.info("Loading %s on %s (batch=%s)", self.model_name, self.device, batch_size)
        self._model = SentenceTransformer(self.model_name, device=self.device)

    def _prefix(self, texts: List[str], *, is_query: bool) -> List[str]:
        if "bge" not in self.model_name.lower():
            return texts
        prefix = QUERY_PREFIX if is_query else DOC_PREFIX
        return [prefix + (t or "") for t in texts]

    def _encode(self, texts: List[str], *, is_query: bool) -> List[List[float]]:
        if not texts:
            return []
        inputs = self._prefix(texts, is_query=is_query)
        vectors = self._model.encode(
            inputs,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(inputs) > 64,
        )
        return [v.tolist() for v in vectors]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._encode(texts, is_query=False)

    def embed_query(self, text: str) -> List[float]:
        return self._encode([text], is_query=True)[0]
