"""Configuration settings for the multi-agent mechanic workflow."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent

# Load local env first, then backend env as a fallback for shared local development.
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR.parent / "backend" / ".env", override=False)

# API Keys (OpenAI-compatible providers use the same ChatOpenAI wiring)
OPENAI_API_KEY = (
    os.getenv("OPENAI_API_KEY", "").strip()
    or os.getenv("BIGMODEL_API_KEY", "").strip()
    or os.getenv("LLM_API_KEY", "").strip()
)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
base_url = (os.getenv("BASE_URL", os.getenv("OPENAI_BASE_URL", "")) or "").strip()

# Paths
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
USER_DATA_PATH = os.getenv("USER_DATA_PATH", "./data/users")
SAMPLE_DATA_PATH = "./data/sample_obd2_data.json"
RAG_SOURCES_DIR = os.getenv("RAG_SOURCES_DIR", "./data/sources")
RAG_MANUALS_DIR = os.path.join(RAG_SOURCES_DIR, "manuals")
RAG_DTC_DIR = os.path.join(RAG_SOURCES_DIR, "dtc")

# Model Configuration (default: Zhipu BigModel GLM — see https://docs.bigmodel.cn/)
LLM_MODEL = os.getenv("LLM_MODEL", "glm-5.1")

# Default endpoint when unset: BigModel OpenAI-compatible API
if not base_url:
    base_url = "https://open.bigmodel.cn/api/paas/v4"

# Agent-specific model settings
AGENT_MODELS = {
    "obd2_writer": {
        "model": LLM_MODEL,
        "temperature": 0.3,
    },
    "obd2_observer": {
        "model": LLM_MODEL,
        "temperature": 0.2,
    },
    "product_researcher": {
        "model": LLM_MODEL,
        "temperature": 0.4,
    },
    "technical_writer": {
        "model": LLM_MODEL,
        "temperature": 0.3,
    },
    "formatter": {
        "model": LLM_MODEL,
        "temperature": 0.5,
    },
}

# Retrieve-Reflect-Retry Configuration
MAX_RETRY_CYCLES = int(os.getenv("MAX_RETRY_CYCLES", "1"))
MAX_REVISION_CYCLES = int(os.getenv("MAX_REVISION_CYCLES", "1"))
REFLECTION_SCORE_THRESHOLD = 0.7

# RAG Configuration
RAG_RETRIEVE_K = int(os.getenv("RAG_RETRIEVE_K", "50"))  # hybrid candidates before rerank
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))  # final chunks after rerank
RAG_HYBRID_ENABLED = os.getenv("RAG_HYBRID_ENABLED", "true").strip().lower() in ("1", "true", "yes")
RAG_RERANK_ENABLED = os.getenv("RAG_RERANK_ENABLED", "true").strip().lower() in ("1", "true", "yes")
RAG_RERANK_MODEL = os.getenv("RAG_RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RAG_RRF_K = int(os.getenv("RAG_RRF_K", "60"))
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-m3")
RAG_EMBEDDING_DEVICE = os.getenv("RAG_EMBEDDING_DEVICE", "auto")  # auto | cuda | cpu
RAG_EMBEDDING_BATCH_SIZE = int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "16"))
# auto | st | fastembed | flag — production default uses sentence-transformers on CUDA
RAG_EMBEDDING_BACKEND = os.getenv("RAG_EMBEDDING_BACKEND", "auto")
RAG_EMBEDDING_DIM = 1024  # BGE-M3 / BGE-large dense dimension (fake embeddings in tests use this when set)
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
# Manuals only — DTC records are always one chunk per code (see src/rag/ingest/ingest_policy.py)
RAG_MANUAL_CHUNK_SIZE = int(os.getenv("RAG_MANUAL_CHUNK_SIZE", str(RAG_CHUNK_SIZE)))
RAG_MANUAL_CHUNK_OVERLAP = int(os.getenv("RAG_MANUAL_CHUNK_OVERLAP", str(RAG_CHUNK_OVERLAP)))

# Agent runtime limits (reduce long tail latency)
AGENT_LLM_TIMEOUT_SEC = int(os.getenv("AGENT_LLM_TIMEOUT_SEC", "240"))
AGENT_LLM_MAX_RETRIES = int(os.getenv("AGENT_LLM_MAX_RETRIES", "1"))

# Web search tuning (keep search enabled but faster)
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "basic")
TAVILY_TIMEOUT_SEC = int(os.getenv("TAVILY_TIMEOUT_SEC", "8"))
TAVILY_CACHE_TTL_SEC = int(os.getenv("TAVILY_CACHE_TTL_SEC", "600"))
TAVILY_MAX_RESULTS_DEFAULT = int(os.getenv("TAVILY_MAX_RESULTS_DEFAULT", "3"))

# Product search tuning
PRODUCT_SEARCH_MAX_TYPES = int(os.getenv("PRODUCT_SEARCH_MAX_TYPES", "2"))
PRODUCT_SEARCH_RESULTS_PER_TYPE = int(os.getenv("PRODUCT_SEARCH_RESULTS_PER_TYPE", "2"))
PRODUCT_SEARCH_DOMAINS = os.getenv(
    "PRODUCT_SEARCH_DOMAINS",
    "amazon.com,rockauto.com,advanceautoparts.com,autozone.com,oreillyauto.com,"
    "parts.toyota.com,toyotapartsdeal.com,tpmsdirect.com",
).split(",")

# Retrieval observability
RAG_TRACE_VECTORS = os.getenv("RAG_TRACE_VECTORS", "true").strip().lower() in ("1", "true", "yes")
RAG_VECTOR_PREVIEW_DIMS = int(os.getenv("RAG_VECTOR_PREVIEW_DIMS", "8"))

# Prompt-size guards
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))
PRODUCT_NEEDS_ANALYSIS_CHARS = int(os.getenv("PRODUCT_NEEDS_ANALYSIS_CHARS", "4000"))
TECH_WRITER_ANALYSIS_CHARS = int(os.getenv("TECH_WRITER_ANALYSIS_CHARS", "7000"))
FORMATTER_DRAFT_CHARS = int(os.getenv("FORMATTER_DRAFT_CHARS", "9000"))

# Memory Configuration
MAX_CONVERSATION_HISTORY = 10

