"""ONNX embeddings via fastembed — CPU fallback when PyTorch GPU is unavailable."""
from __future__ import annotations

import logging
from typing import List

from fastembed import TextEmbedding

from src.rag.sentence_transformer_embeddings import effective_embedding_model

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-large-en-v1.5"


def _onnx_cuda_usable() -> bool:
    try:
        import onnxruntime as ort

        return "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:
        return False


class FastEmbedEmbeddings:
    """LangChain-compatible embeddings using fastembed (ONNX)."""

    def __init__(self, model_name: str | None = None, *, use_cuda: bool = False) -> None:
        resolved = effective_embedding_model(model_name or DEFAULT_MODEL)
        cuda = use_cuda and _onnx_cuda_usable()
        if use_cuda and not cuda:
            logger.warning("fastembed: CUDA ONNX provider unavailable; using CPU")
        self.model_name = resolved
        self._model = TextEmbedding(resolved, cuda=cuda)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [vec.tolist() for vec in self._model.embed(texts)]

    def embed_query(self, text: str) -> List[float]:
        return next(self._model.embed([text])).tolist()
