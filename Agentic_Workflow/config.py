"""Configuration settings for the multi-agent mechanic workflow."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent

# Load local env first, then backend env as a fallback for shared local development.
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR.parent / "backend" / ".env", override=False)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
base_url = os.getenv("BASE_URL", os.getenv("OPENAI_BASE_URL", ""))

# Paths
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
USER_DATA_PATH = os.getenv("USER_DATA_PATH", "./data/users")
SAMPLE_DATA_PATH = "./data/sample_obd2_data.json"

# Model Configuration
DEEPSEEK_MODEL = "deepseek-chat"

# If DeepSeek model is selected and no base URL is configured, use DeepSeek default endpoint.
if not base_url:
    base_url = "https://api.deepseek.com/v1"

# Agent-specific model settings
AGENT_MODELS = {
    "obd2_writer": {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.3,
    },
    "obd2_observer": {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.2,
    },
    "product_researcher": {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.4,
    },
    "technical_writer": {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.3,
    },
    "formatter": {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.5,
    },
}

# Retrieve-Reflect-Retry Configuration
MAX_RETRY_CYCLES = 3
REFLECTION_SCORE_THRESHOLD = 0.7

# RAG Configuration
RAG_TOP_K = 5
RAG_CHUNK_SIZE = 1000
RAG_CHUNK_OVERLAP = 200

# Memory Configuration
MAX_CONVERSATION_HISTORY = 10

