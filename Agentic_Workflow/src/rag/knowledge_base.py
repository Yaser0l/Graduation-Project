"""RAG Knowledge Base system for automotive data."""
from __future__ import annotations

import logging
import os
import platform
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

import config
from src.rag.bm25_index import BM25Index
from src.rag.hybrid import reciprocal_rank_fusion
from src.rag.ingest.manual_chunking import chunk_manual_document
from src.rag.retrieval_trace import (
    RetrievalTrace,
    ScoredHit,
    chroma_distance_to_cosine,
    cosine_similarity,
    format_trace,
    vector_preview,
)

logger = logging.getLogger(__name__)


def _use_fake_embeddings() -> bool:
    return os.environ.get("RAG_USE_FAKE_EMBEDDINGS", "").strip().lower() in ("1", "true", "yes")


def _embedding_backend() -> str:
    return os.environ.get("RAG_EMBEDDING_BACKEND", "auto").strip().lower()


def _hybrid_enabled() -> bool:
    return getattr(config, "RAG_HYBRID_ENABLED", True) and not _use_fake_embeddings()


def _rerank_enabled() -> bool:
    return getattr(config, "RAG_RERANK_ENABLED", True) and not _use_fake_embeddings()


def resolve_embedding_function(embedding_function: Optional[Any] = None) -> Any:
    """Return embeddings for Chroma (BGE on GPU via sentence-transformers when CUDA is available)."""
    if embedding_function is not None:
        return embedding_function
    if _use_fake_embeddings():
        from src.rag.deterministic_embeddings import DeterministicEmbeddings

        return DeterministicEmbeddings(dim=config.RAG_EMBEDDING_DIM)

    model = getattr(config, "RAG_EMBEDDING_MODEL", "BAAI/bge-m3")
    device = getattr(config, "RAG_EMBEDDING_DEVICE", "auto")
    batch = getattr(config, "RAG_EMBEDDING_BATCH_SIZE", 16)
    backend = _embedding_backend()

    if backend == "fastembed":
        from src.rag.fastembed_embeddings import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=model, use_cuda=device in ("cuda", "gpu", "auto"))

    if backend == "flag":
        from src.rag.bge_m3_embeddings import BGEM3Embeddings

        return BGEM3Embeddings(model_name=model, device=device, batch_size=batch)

    from src.rag.bge_m3_embeddings import resolve_torch_device

    torch_device = resolve_torch_device(device)
    if backend in ("st", "sentence-transformers") or torch_device == "cuda" or backend == "auto":
        from src.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings

        return SentenceTransformerEmbeddings(
            model_name=model,
            device=device,
            batch_size=batch,
        )

    if backend == "auto" and platform.system() == "Windows":
        from src.rag.fastembed_embeddings import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=model)

    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=model,
        model_kwargs={"device": torch_device},
        encode_kwargs={"normalize_embeddings": True},
    )


def _dtc_chunk_id(meta: Dict[str, Any]) -> str:
    code = (meta.get("code") or "unknown").upper()
    make = (meta.get("make") or "generic").lower()
    return f"dtc:{make}:{code}"


def _split_documents(
    documents: List[Document],
    chunk_size: int,
    chunk_overlap: int,
    *,
    manual_chunk_size: Optional[int] = None,
    manual_chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """Split documents; DTC rows stay atomic; manuals use section-aware chunking."""
    m_size = manual_chunk_size or chunk_size
    m_overlap = manual_chunk_overlap if manual_chunk_overlap is not None else chunk_overlap
    chunks: List[Document] = []
    for doc in documents:
        text = doc.page_content or ""
        if not text.strip():
            continue
        doc_type = (doc.metadata or {}).get("type")
        if doc_type == "dtc":
            meta = dict(doc.metadata)
            meta["chunk_id"] = _dtc_chunk_id(meta)
            chunks.append(Document(page_content=text, metadata=meta))
            continue
        if doc_type == "manual":
            chunks.extend(
                chunk_manual_document(doc, chunk_size=m_size, chunk_overlap=m_overlap)
            )
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end]
            if chunk_text.strip():
                meta = dict(doc.metadata)
                meta.setdefault("chunk_id", f"generic:{hash(chunk_text) & 0xFFFFFFFF:x}")
                chunks.append(Document(page_content=chunk_text, metadata=meta))
            if end >= len(text):
                break
            start = max(start + 1, end - chunk_overlap)
    return chunks


def _distance_to_similarity(distance: float) -> float:
    return chroma_distance_to_cosine(distance)


class AutomotiveKnowledgeBase:
    """Manages the RAG knowledge base for automotive repair information."""

    COLLECTION_NAME = "automotive_knowledge"

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.persist_directory = persist_directory or config.CHROMA_DB_PATH
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        self.embeddings = resolve_embedding_function(embedding_function)
        self._bm25_index: Optional[BM25Index] = None
        self._bm25_path = Path(self.persist_directory) / "bm25_index.pkl"

        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name=self.COLLECTION_NAME,
        )

        self._chunk_size = config.RAG_CHUNK_SIZE
        self._chunk_overlap = config.RAG_CHUNK_OVERLAP
        self._manual_chunk_size = getattr(config, "RAG_MANUAL_CHUNK_SIZE", config.RAG_CHUNK_SIZE)
        self._manual_chunk_overlap = getattr(
            config, "RAG_MANUAL_CHUNK_OVERLAP", config.RAG_CHUNK_OVERLAP
        )
        self._load_bm25_index()

    def _load_bm25_index(self) -> None:
        if self._bm25_path.exists():
            try:
                self._bm25_index = BM25Index.load(self._bm25_path)
            except Exception as exc:
                logger.warning("Could not load BM25 index: %s", exc)
                self._bm25_index = None

    def rebuild_bm25_index(self) -> None:
        """Rebuild lexical index from the current Chroma collection."""
        if not _hybrid_enabled():
            return
        collection = self.vector_store._collection
        total = collection.count()
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        chunk_ids: List[str] = []
        page_size = 400
        offset = 0
        while offset < total:
            batch = collection.get(
                include=["documents", "metadatas"],
                limit=page_size,
                offset=offset,
            )
            batch_texts = batch.get("documents") or []
            batch_metas = batch.get("metadatas") or []
            for idx, text in enumerate(batch_texts):
                meta = batch_metas[idx] if idx < len(batch_metas) else {}
                meta = meta or {}
                texts.append(text or "")
                metas.append(meta)
                chunk_ids.append(meta.get("chunk_id") or f"row:{len(chunk_ids)}")
            offset += page_size
        if not texts:
            self._bm25_index = None
            if self._bm25_path.exists():
                self._bm25_path.unlink()
            return
        self._bm25_index = BM25Index.build(texts, metas, chunk_ids)
        self._bm25_index.save(self._bm25_path)
        logger.info("BM25 index rebuilt (%s chunks)", len(texts))

    def add_documents(self, documents: List[Document], batch_size: int = 500) -> None:
        chunks = _split_documents(
            documents,
            self._chunk_size,
            self._chunk_overlap,
            manual_chunk_size=self._manual_chunk_size,
            manual_chunk_overlap=self._manual_chunk_overlap,
        )
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            if batch:
                self.vector_store.add_documents(batch)
        self.rebuild_bm25_index()

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> None:
        docs = [
            Document(page_content=t, metadata=(metadatas[i] if metadatas else {}))
            for i, t in enumerate(texts)
        ]
        self.add_documents(docs)

    def _candidate_k(self, k: Optional[int]) -> int:
        return max(k or config.RAG_TOP_K, getattr(config, "RAG_RETRIEVE_K", 50))

    def _final_k(self, k: Optional[int]) -> int:
        return k or config.RAG_TOP_K

    def _dense_search(
        self,
        query: str,
        candidate_k: int,
        filter_dict: Optional[Dict[str, Any]],
    ) -> List[Tuple[Document, float]]:
        if filter_dict:
            return self.vector_store.similarity_search_with_score(
                query, k=candidate_k, filter=filter_dict
            )
        return self.vector_store.similarity_search_with_score(query, k=candidate_k)

    def _dense_candidates(
        self,
        query: str,
        candidate_k: int,
        filter_dict: Optional[Dict[str, Any]],
    ) -> Tuple[List[Tuple[str, float]], Dict[str, Tuple[Document, float]]]:
        pairs = self._dense_search(query, candidate_k, filter_dict)
        ranking: List[Tuple[str, float]] = []
        doc_map: Dict[str, Tuple[Document, float]] = {}
        for doc, distance in pairs:
            meta = doc.metadata or {}
            chunk_id = meta.get("chunk_id") or doc.page_content[:80]
            doc_map[chunk_id] = (doc, float(distance))
            ranking.append((chunk_id, _distance_to_similarity(distance)))
        return ranking, doc_map

    def lookup_dtc_code(self, code: str, make: str | None = None) -> Optional[Document]:
        """Exact metadata lookup for one OBD-II code (preferred over semantic search)."""
        code = code.upper().strip()
        collection = self.vector_store._collection
        try:
            result = collection.get(
                where={"$and": [{"type": {"$eq": "dtc"}}, {"code": {"$eq": code}}]},
                limit=20,
                include=["documents", "metadatas"],
            )
        except Exception:
            return None
        texts = result.get("documents") or []
        metas = result.get("metadatas") or []
        if not texts:
            return None
        if make:
            want = make.lower()
            for text, meta in zip(texts, metas):
                m = (meta or {}).get("make") or ""
                if m.lower() in (want, "generic"):
                    return Document(page_content=text, metadata=dict(meta or {}))
        return Document(page_content=texts[0], metadata=dict(metas[0] or {}))

    def _bm25_candidates(
        self,
        query: str,
        candidate_k: int,
        filter_dict: Optional[Dict[str, Any]],
    ) -> List[Tuple[str, float]]:
        if not self._bm25_index:
            return []
        return self._bm25_index.search(query, k=candidate_k, filter_dict=filter_dict)

    def _documents_for_chunk_ids(self, chunk_ids: List[str]) -> List[Document]:
        docs: List[Document] = []
        for chunk_id in chunk_ids:
            if self._bm25_index:
                doc = self._bm25_index.document_for_chunk_id(chunk_id)
                if doc:
                    docs.append(doc)
                    continue
            # Fallback: query Chroma by metadata chunk_id if BM25 doc missing
            try:
                found = self.vector_store.similarity_search(
                    chunk_id,
                    k=1,
                    filter={"chunk_id": chunk_id},
                )
                if found:
                    docs.append(found[0])
            except Exception:
                pass
        return docs

    def retrieve_detailed(
        self,
        query: str,
        k: int = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        *,
        include_vector_preview: bool | None = None,
    ) -> Tuple[List[Tuple[Document, float]], RetrievalTrace]:
        """Hybrid retrieve with full score breakdown and optional embedding previews."""
        final_k = self._final_k(k)
        candidate_k = self._candidate_k(k)
        trace = RetrievalTrace(
            query=query,
            hybrid_enabled=_hybrid_enabled(),
            rerank_enabled=_rerank_enabled(),
        )
        want_vectors = (
            include_vector_preview
            if include_vector_preview is not None
            else getattr(config, "RAG_TRACE_VECTORS", True)
        )
        preview_dims = getattr(config, "RAG_VECTOR_PREVIEW_DIMS", 8)
        query_vec: Optional[List[float]] = None
        if want_vectors:
            try:
                query_vec = self.embeddings.embed_query(query)
            except Exception as exc:
                trace.notes.append(f"query embedding failed: {exc}")

        dense_ranking, dense_doc_map = self._dense_candidates(query, candidate_k, filter_dict)
        bm25_hits = self._bm25_candidates(query, candidate_k, filter_dict) if _hybrid_enabled() else []
        bm25_map = {cid: score for cid, score in bm25_hits}

        if not _hybrid_enabled() and not _rerank_enabled():
            pairs = self._dense_search(query, final_k, filter_dict)
            results = [(doc, chroma_distance_to_cosine(dist)) for doc, dist in pairs]
            for rank, (doc, dist) in enumerate(pairs, start=1):
                meta = doc.metadata or {}
                cid = meta.get("chunk_id", "")
                cos = chroma_distance_to_cosine(dist)
                doc_prev = None
                if want_vectors and query_vec:
                    try:
                        dv = self.embeddings.embed_documents([doc.page_content])[0]
                        cos = cosine_similarity(query_vec, dv)
                        doc_prev = vector_preview(dv, preview_dims)
                    except Exception:
                        pass
                trace.hits.append(
                    ScoredHit(
                        rank=rank,
                        chunk_id=cid,
                        content=doc.page_content,
                        metadata=dict(meta),
                        dense_distance=float(dist),
                        cosine_similarity=cos,
                        final_score=cos,
                        source="dense",
                        query_vector_preview=vector_preview(query_vec, preview_dims) if query_vec else None,
                        doc_vector_preview=doc_prev,
                        embedding_dim=len(query_vec) if query_vec else 0,
                    )
                )
            trace.candidate_count = len(pairs)
            return results, trace

        rankings: List[List[Tuple[str, float]]] = [dense_ranking]
        if bm25_hits:
            rankings.append(bm25_hits)

        if len(rankings) == 1:
            fused = dense_ranking[:candidate_k]
        else:
            fused = reciprocal_rank_fusion(
                rankings,
                rrf_k=getattr(config, "RAG_RRF_K", 60),
                top_n=candidate_k,
            )
        rrf_map = {cid: score for cid, score in fused}
        trace.candidate_count = len(fused)

        chunk_ids = [cid for cid, _ in fused]
        doc_by_id: Dict[str, Document] = {}
        for cid in chunk_ids:
            if cid in dense_doc_map:
                doc_by_id[cid] = dense_doc_map[cid][0]
        for cid in chunk_ids:
            if cid not in doc_by_id and self._bm25_index:
                doc = self._bm25_index.document_for_chunk_id(cid)
                if doc:
                    doc_by_id[cid] = doc
        candidates = [doc_by_id[cid] for cid in chunk_ids if cid in doc_by_id]

        if not candidates:
            trace.notes.append("fusion produced no documents; falling back to dense")
            pairs = self._dense_search(query, final_k, filter_dict)
            return [(d, chroma_distance_to_cosine(s)) for d, s in pairs], trace

        if _rerank_enabled():
            from src.rag.reranker import get_reranker

            reranker = get_reranker(
                getattr(config, "RAG_RERANK_MODEL", "BAAI/bge-reranker-v2-m3"),
                device=getattr(config, "RAG_EMBEDDING_DEVICE", "auto"),
            )
            ranked = reranker.rerank(query, candidates, top_n=final_k)
        else:
            score_map = rrf_map
            ranked = [(doc, score_map.get((doc.metadata or {}).get("chunk_id", ""), 0.0)) for doc in candidates[:final_k]]

        results: List[Tuple[Document, float]] = []
        for rank, (doc, final_score) in enumerate(ranked, start=1):
            meta = doc.metadata or {}
            cid = meta.get("chunk_id", "")
            dense_dist = dense_doc_map.get(cid, (None, None))[1]
            cos = chroma_distance_to_cosine(dense_dist) if dense_dist is not None else None
            doc_prev = None
            if want_vectors and query_vec:
                try:
                    dv = self.embeddings.embed_documents([doc.page_content])[0]
                    cos = cosine_similarity(query_vec, dv)
                    doc_prev = vector_preview(dv, preview_dims)
                except Exception:
                    pass
            hit = ScoredHit(
                rank=rank,
                chunk_id=cid,
                content=doc.page_content,
                metadata=dict(meta),
                dense_distance=dense_dist,
                cosine_similarity=cos,
                bm25_score=bm25_map.get(cid),
                rrf_score=rrf_map.get(cid),
                rerank_score=float(final_score) if _rerank_enabled() else None,
                final_score=float(final_score),
                source="rerank" if _rerank_enabled() else "hybrid",
                query_vector_preview=vector_preview(query_vec, preview_dims) if query_vec else None,
                doc_vector_preview=doc_prev,
                embedding_dim=len(query_vec) if query_vec else 0,
            )
            trace.hits.append(hit)
            results.append((doc, float(final_score)))
        return results, trace

    def retrieve_with_scores(
        self,
        query: str,
        k: int = None,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """Hybrid retrieve (dense + BM25) with optional cross-encoder rerank."""
        docs_scores, _trace = self.retrieve_detailed(query, k=k, filter_dict=filter_dict)
        return docs_scores

    def retrieve(
        self,
        query: str,
        k: int = None,
        filter_dict: Optional[Dict] = None,
    ) -> List[Document]:
        return [doc for doc, _ in self.retrieve_with_scores(query, k=k, filter_dict=filter_dict)]

    def reflect_on_retrieval(
        self,
        query: str,
        retrieved_docs: List[Document],
        threshold: float = None,
    ) -> Tuple[bool, float, str]:
        threshold = threshold or config.REFLECTION_SCORE_THRESHOLD

        if not retrieved_docs:
            return False, 0.0, "No documents retrieved. Consider reformulating query or using web search."

        docs_with_scores = self.retrieve_with_scores(query, k=len(retrieved_docs))
        if not docs_with_scores:
            return False, 0.0, "Unable to score documents."

        scores = [score for _, score in docs_with_scores]
        avg_score = sum(scores) / len(scores)
        is_sufficient = avg_score >= threshold

        if is_sufficient:
            reflection = (
                f"Retrieved {len(retrieved_docs)} relevant documents with average score "
                f"{avg_score:.2f}. Sufficient for analysis."
            )
        else:
            reflection = (
                f"Retrieved documents have low relevance (avg score: {avg_score:.2f}). "
                "Consider web search or query reformulation."
            )

        return is_sufficient, avg_score, reflection

    def initialize_with_sample_data(self) -> None:
        obd2_codes = [
            {
                "text": "C0561 - System Disabled Information Stored. This code indicates that the ABS system has been disabled and the information has been stored in the control module memory. Common causes include faulty wheel speed sensors, damaged wiring, or control module issues. Check wheel speed sensors and wiring connections.",
                "metadata": {"type": "dtc", "system": "chassis", "code": "C0561", "make": "generic"},
            },
            {
                "text": "C0750 - Tire Pressure Monitor Sensor Battery Low. This diagnostic code indicates that one or more TPMS (Tire Pressure Monitoring System) sensors have a low battery. The TPMS sensor batteries typically last 5-10 years. When this code appears, the affected sensor(s) need to be replaced. The tire pressure should also be checked and adjusted to manufacturer specifications.",
                "metadata": {"type": "dtc", "system": "chassis", "code": "C0750", "make": "generic"},
            },
            {
                "text": "P0420 - Catalyst System Efficiency Below Threshold (Bank 1). This code indicates that the catalytic converter is not operating efficiently. Common causes include a failing catalytic converter, oxygen sensor issues, exhaust leaks, or engine misfires. Diagnosis should include checking oxygen sensor readings and exhaust system inspection.",
                "metadata": {"type": "dtc", "system": "engine", "code": "P0420", "make": "generic"},
            },
            {
                "text": "P0301 - Cylinder 1 Misfire Detected. This code indicates that cylinder 1 is experiencing misfires. Common causes include faulty spark plugs, ignition coils, fuel injectors, low compression, or vacuum leaks. Start diagnosis with spark plug and ignition coil inspection.",
                "metadata": {"type": "dtc", "system": "engine", "code": "P0301", "make": "generic"},
            },
        ]
        tire_info = [
            {
                "text": "Proper tire pressure is critical for vehicle safety and performance. Underinflated tires can lead to poor handling, increased tire wear, reduced fuel economy, and potential tire failure. Most passenger vehicles require 30-35 PSI. Always check tire pressure when tires are cold. The recommended pressure is found on the driver's door jamb sticker.",
                "metadata": {"type": "maintenance", "category": "tires"},
            },
        ]
        all_texts, all_metadatas = [], []
        for item in obd2_codes + tire_info:
            all_texts.append(item["text"])
            all_metadatas.append(item["metadata"])
        self.add_texts(all_texts, all_metadatas)

    def reset_collection(self) -> None:
        try:
            self.vector_store.delete_collection()
        except Exception:
            pass
        self._bm25_index = None
        if self._bm25_path.exists():
            self._bm25_path.unlink()
        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name=self.COLLECTION_NAME,
        )

    def get_stats(self) -> Dict[str, Any]:
        collection = self.vector_store._collection
        total = collection.count()
        type_counts: Counter = Counter()
        make_counts: Counter = Counter()
        try:
            offset = 0
            page_size = 400
            while offset < total:
                result = collection.get(
                    include=["metadatas"],
                    limit=page_size,
                    offset=offset,
                )
                for meta in result.get("metadatas") or []:
                    if not meta:
                        continue
                    doc_type = meta.get("type") or "unknown"
                    type_counts[doc_type] += 1
                    if doc_type == "dtc":
                        make_counts[meta.get("make") or "unknown"] += 1
                offset += page_size
        except Exception:
            pass
        return {
            "total_chunks": total,
            "dtc": type_counts.get("dtc", 0),
            "manual": type_counts.get("manual", 0),
            "by_make_dtc": dict(make_counts),
            "hybrid_enabled": _hybrid_enabled(),
            "rerank_enabled": _rerank_enabled(),
        }

    def get_collection_count(self) -> int:
        return self.vector_store._collection.count()


def get_knowledge_base(persist_directory: Optional[str] = None) -> AutomotiveKnowledgeBase:
    if persist_directory is not None:
        return AutomotiveKnowledgeBase(persist_directory=persist_directory)
    return _default_knowledge_base()


_default_kb: Optional[AutomotiveKnowledgeBase] = None


def _default_knowledge_base() -> AutomotiveKnowledgeBase:
    global _default_kb
    if _default_kb is None:
        _default_kb = AutomotiveKnowledgeBase()
    return _default_kb


class _LazyKnowledgeBase:
    def __getattr__(self, name: str):
        return getattr(_default_knowledge_base(), name)


knowledge_base = _LazyKnowledgeBase()
