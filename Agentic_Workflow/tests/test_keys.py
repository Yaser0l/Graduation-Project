"""Connectivity tests for API keys and base URLs."""
import os
import sys
from pathlib import Path
# Ensure project root is on sys.path when running this file directly
sys.path.insert(0, str(Path(__file__).parent.parent))
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
import config


def mask_key(key: str) -> str:
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def test_openai_chat() -> bool:
    print("=" * 60)
    print("TEST: DeepSeek Chat connectivity (via OpenAI key)")
    print("=" * 60)

    print(f"OPENAI_API_KEY: {mask_key(config.OPENAI_API_KEY)}")
    print(f"BASE_URL used: {config.base_url or '<default>'}")

    llm_kwargs = {
        "model": "deepseek-chat",
        "temperature": 0.0,
        "api_key": config.OPENAI_API_KEY,
    }
    if config.base_url:
        llm_kwargs["base_url"] = config.base_url

    try:
        llm = ChatOpenAI(**llm_kwargs)
        resp = llm.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Reply with exactly: OK"),
        ])
        ok = resp.content.strip() == "OK"
        print(f"Chat response: {resp.content!r}")
        print("Chat connectivity OK" if ok else "Unexpected chat response")
        return ok
    except Exception as e:
        print(f"Chat test failed: {e}")
        return False


def test_hf_embeddings() -> bool:
    print("\n" + "=" * 60)
    print("TEST: HuggingFace Embeddings (Local)")
    print("=" * 60)

    try:
        emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vec = emb.embed_query("test")
        ok = isinstance(vec, list) and len(vec) > 0
        print(f"Embedding length: {len(vec) if isinstance(vec, list) else 'N/A'}")
        print("Embeddings connectivity OK" if ok else "Embeddings returned invalid vector")
        return ok
    except Exception as e:
        print(f"Embeddings test failed: {e}")
        return False


def ask_question(question: str) -> bool:
    print("\n" + "=" * 60)
    print(f"ASK: {question}")
    print("=" * 60)
    llm_kwargs = {
        "model": config.AGENT_MODELS["obd2_writer"]["model"],
        "temperature": 0.2,
        "api_key": config.OPENAI_API_KEY,
    }
    if config.base_url:
        llm_kwargs["base_url"] = config.base_url
    try:
        llm = ChatOpenAI(**llm_kwargs)
        resp = llm.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=question),
        ])
        print("\nResponse:\n")
        print(resp.content)
        return True
    except Exception as e:
        print(f"Ask failed: {e}")
        return False


def main():
    # Optional: --ask "your question"
    if len(sys.argv) >= 3 and sys.argv[1] == "--ask":
        ok = ask_question(" who's the father of rand althor ".join(sys.argv[2:]))
        sys.exit(0 if ok else 1)
    else:
        chat_ok = test_openai_chat()
        emb_ok = test_hf_embeddings()
        all_ok = chat_ok and emb_ok
        print("\n" + "=" * 60)
        print(f"KEY TEST SUMMARY: {'ALL OK' if all_ok else 'FAILURES'}")
        print("=" * 60)
        sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()


