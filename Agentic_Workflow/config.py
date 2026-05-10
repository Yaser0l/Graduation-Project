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
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_CHUNK_SIZE = 1000
RAG_CHUNK_OVERLAP = 200

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

# Prompt-size guards
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))
PRODUCT_NEEDS_ANALYSIS_CHARS = int(os.getenv("PRODUCT_NEEDS_ANALYSIS_CHARS", "4000"))
TECH_WRITER_ANALYSIS_CHARS = int(os.getenv("TECH_WRITER_ANALYSIS_CHARS", "7000"))
FORMATTER_DRAFT_CHARS = int(os.getenv("FORMATTER_DRAFT_CHARS", "9000"))

# Memory Configuration
MAX_CONVERSATION_HISTORY = 10

