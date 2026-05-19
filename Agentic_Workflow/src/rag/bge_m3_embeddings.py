"""BGE-M3 dense embeddings (GPU when available) — LangChain-compatible."""
from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# BGE-M3 retrieval prompts (BAAI model card — improves asymmetric search)
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
DOC_PREFIX = "Represent this document for retrieval: "


def resolve_torch_device(preferred: Optional[str] = None) -> str:
    """Return 'cuda', 'mps', or 'cpu' based on env and hardware."""
    import torch

    want = (preferred or "auto").strip().lower()
    if want == "cpu":
        return "cpu"
    if want == "mps" and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    if want in ("cuda", "gpu", "auto"):
        if torch.cuda.is_available():
            return "cuda"
    if want == "mps":
        return "cpu"
    return "cpu"


class BGEM3Embeddings:
    """BAAI/bge-m3 via FlagEmbedding (dense vectors for Chroma)."""

    MODEL_NAME = "BAAI/bge-m3"
    EMBEDDING_DIM = 1024

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int = 12,
        use_fp16: bool = True,
    ) -> None:
        from FlagEmbedding import BGEM3FlagModel

        self.model_name = model_name or self.MODEL_NAME
        self.device = resolve_torch_device(device)
        self.batch_size = batch_size
        use_gpu = self.device == "cuda"
        logger.info(
            "Loading %s on %s (fp16=%s, batch=%s)",
            self.model_name,
            self.device,
            use_fp16 and use_gpu,
            batch_size,
        )
        self._model = BGEM3FlagModel(
            self.model_name,
            use_fp16=use_fp16 and use_gpu,
            device=self.device,
        )

    def _encode(self, texts: List[str], *, is_query: bool) -> List[List[float]]:
        prefix = QUERY_PREFIX if is_query else DOC_PREFIX
        inputs = [prefix + (t or "") for t in texts]
        output = self._model.encode(
            inputs,
            batch_size=self.batch_size,
            max_length=8192,
        )
        dense = output["dense_vecs"]
        return [v.tolist() if hasattr(v, "tolist") else list(v) for v in dense]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self._encode(texts, is_query=False)

    def embed_query(self, text: str) -> List[float]:
        return self._encode([text], is_query=True)[0]
