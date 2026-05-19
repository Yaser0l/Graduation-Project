"""Environment checks before running the ingest pipeline."""
from __future__ import annotations

import importlib
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


EXIT_OK = 0
EXIT_PREFLIGHT_FAIL = 2


@dataclass
class PreflightResult:
    ok: bool
    messages: List[str]
    exit_code: int = EXIT_OK


def _check_python_version() -> Optional[str]:
    if sys.version_info < (3, 10):
        return (
            f"Python 3.10+ required (found {sys.version_info.major}.{sys.version_info.minor}). "
            "Use Python 3.11 or 3.12 for best compatibility with sentence-transformers on Windows."
        )
    if sys.version_info >= (3, 13) and platform.system() == "Windows":
        # Warning only — hard fail happens in check_embeddings_import if import crashes.
        return None
    return None


def _check_import(module: str, pip_name: Optional[str] = None) -> Optional[str]:
    try:
        importlib.import_module(module)
        return None
    except ImportError:
        name = pip_name or module
        return f"Missing dependency '{name}'. Install with: pip install {name}"


def check_embeddings_import() -> Optional[str]:
    """Verify embedding stack (sentence-transformers + torch, or fastembed) is available."""
    import importlib.util

    backend = os.environ.get("RAG_EMBEDDING_BACKEND", "auto").strip().lower()

    if backend == "fastembed":
        if importlib.util.find_spec("fastembed") is None:
            return "fastembed is not installed. pip install fastembed"
        return None

    if backend == "flag":
        if importlib.util.find_spec("FlagEmbedding") is None:
            return "FlagEmbedding is not installed. pip install FlagEmbedding"
        try:
            import torch
        except ImportError:
            return "torch is not installed. pip install torch (CUDA build for GPU)"
        return None

    if importlib.util.find_spec("sentence_transformers") is None:
        return "sentence-transformers is not installed. pip install sentence-transformers"
    try:
        import torch
    except ImportError:
        return "torch is not installed. pip install torch (CUDA build for GPU)"
    device = os.environ.get("RAG_EMBEDDING_DEVICE", "auto").lower()
    if device in ("cuda", "gpu") and not torch.cuda.is_available():
        return (
            "CUDA not available in this Python env. Install GPU torch, e.g.: "
            "pip install torch --index-url https://download.pytorch.org/whl/cu124"
        )
    return None


def run_preflight(
    project_root: Path,
    sources_dir: Path,
    chroma_dir: Path,
    *,
    skip_embeddings: bool = False,
) -> PreflightResult:
    """Run all preflight checks. Returns PreflightResult with exit_code 2 on failure."""
    messages: List[str] = []
    errors: List[str] = []

    py_err = _check_python_version()
    if py_err:
        errors.append(py_err)

    for mod, pip in [
        ("httpx", "httpx"),
        ("pypdf", "pypdf"),
        ("chromadb", "chromadb"),
        ("yaml", "pyyaml"),
    ]:
        err = _check_import(mod, pip)
        if err:
            errors.append(err)

    if not skip_embeddings:
        emb_err = check_embeddings_import()
        if emb_err:
            errors.append(emb_err)
        else:
            try:
                import torch

                if torch.cuda.is_available():
                    messages.append(
                        f"Embeddings: {os.environ.get('RAG_EMBEDDING_MODEL', 'BAAI/bge-m3')} "
                        f"on GPU ({torch.cuda.get_device_name(0)})"
                    )
                else:
                    messages.append(
                        f"Embeddings: {os.environ.get('RAG_EMBEDDING_MODEL', 'BAAI/bge-m3')} on CPU "
                        "(set RAG_EMBEDDING_DEVICE=cuda after installing CUDA torch)"
                    )
            except ImportError:
                pass

    for label, path in [("sources", sources_dir), ("chroma", chroma_dir)]:
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
        except OSError as exc:
            errors.append(f"Cannot write to {label} directory {path}: {exc}")

    if errors:
        messages.extend(errors)
        return PreflightResult(ok=False, messages=messages, exit_code=EXIT_PREFLIGHT_FAIL)

    messages.append("Preflight checks passed.")
    return PreflightResult(ok=True, messages=messages, exit_code=EXIT_OK)
