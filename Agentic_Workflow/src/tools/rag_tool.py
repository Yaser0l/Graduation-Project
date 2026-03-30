"""RAG retrieval tool."""
from typing import List, Dict, Any
from langchain_core.tools import tool
from src.rag.knowledge_base import knowledge_base


@tool
def retrieve_automotive_knowledge(query: str, top_k: int = 5) -> str:
    """Retrieve relevant automotive repair information from the knowledge base.
    
    Args:
        query: The search query (e.g., OBD2 code, symptom, or repair question)
        top_k: Number of relevant documents to retrieve
        
    Returns:
        Formatted string containing relevant information
    """
    # Retrieve documents
    docs = knowledge_base.retrieve(query, k=top_k)
    
    if not docs:
        return "No relevant information found in the knowledge base."
    
    # Format results
    results = []
    for i, doc in enumerate(docs, 1):
        metadata_str = ", ".join([f"{k}: {v}" for k, v in doc.metadata.items()])
        results.append(f"[Result {i}]\n{doc.page_content}\nMetadata: {metadata_str}\n")
    
    return "\n".join(results)


@tool
def retrieve_with_reflection(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Retrieve automotive information with quality reflection.
    
    This implements the Retrieve-Reflect pattern by evaluating the quality
    of retrieved documents.
    
    Args:
        query: The search query
        top_k: Number of documents to retrieve
        
    Returns:
        Dictionary with retrieved content, quality metrics, and reflection
    """
    # Retrieve documents
    docs = knowledge_base.retrieve(query, k=top_k)
    
    if not docs:
        return {
            "content": "No relevant information found.",
            "is_sufficient": False,
            "score": 0.0,
            "reflection": "No documents retrieved. Consider web search.",
            "document_count": 0
        }
    
    # Reflect on quality
    is_sufficient, avg_score, reflection = knowledge_base.reflect_on_retrieval(query, docs)
    
    # Format content
    content_parts = []
    for i, doc in enumerate(docs, 1):
        content_parts.append(f"[Source {i}] {doc.page_content}")
    
    content = "\n\n".join(content_parts)
    
    return {
        "content": content,
        "is_sufficient": is_sufficient,
        "score": avg_score,
        "reflection": reflection,
        "document_count": len(docs)
    }


def retrieve_for_codes(codes: List[str]) -> str:
    """Retrieve information for multiple OBD2 codes.
    
    Args:
        codes: List of OBD2 codes (e.g., ['C0561', 'C0750'])
        
    Returns:
        Combined information for all codes
    """
    results = []
    
    for code in codes:
        query = f"OBD2 code {code} diagnostic trouble code meaning causes repair"
        docs = knowledge_base.retrieve(query, k=3)
        
        if docs:
            results.append(f"=== Information for {code} ===")
            for doc in docs:
                results.append(doc.page_content)
            results.append("")
    
    return "\n".join(results) if results else "No information found for the provided codes."

