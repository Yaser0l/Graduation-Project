"""Configuration settings for the multi-agent mechanic workflow."""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
base_url = os.getenv("BASE_URL", os.getenv("OPENAI_BASE_URL", ""))

# Paths
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
USER_DATA_PATH = os.getenv("USER_DATA_PATH", "./data/users")
SAMPLE_DATA_PATH = "./data/sample_obd2_data.json"

# Model Configuration
OPENAI_MODEL_GPT4 = "gpt-4o"
OPENAI_MODEL_GPT35 = "gpt-4o-mini"
6
# Agent-specific model settings
AGENT_MODELS = {
    "obd2_writer": {
        "model": OPENAI_MODEL_GPT4,
        "temperature": 0.3,
    },
    "obd2_observer": {
        "model": OPENAI_MODEL_GPT4,
        "temperature": 0.2,
    },
    "product_researcher": {
        "model": OPENAI_MODEL_GPT35,
        "temperature": 0.4,
    },
    "technical_writer": {
        "model": OPENAI_MODEL_GPT4,
        "temperature": 0.3,
    },
    "formatter": {
        "model": OPENAI_MODEL_GPT35,
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

