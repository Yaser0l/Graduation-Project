"""RAG Knowledge Base system for automotive data."""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config


class AutomotiveKnowledgeBase:
    """Manages the RAG knowledge base for automotive repair information."""

    def __init__(self, persist_directory: Optional[str] = None):
        """Initialize the knowledge base.
        
        Args:
            persist_directory: Directory to persist the vector store
        """
        self.persist_directory = persist_directory or config.CHROMA_DB_PATH
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        embedding_params = {"openai_api_key": config.OPENAI_API_KEY}
        if config.base_url:
            embedding_params["openai_api_base"] = config.base_url
        self.embeddings = OpenAIEmbeddings(**embedding_params)
        
        # Initialize or load vector store
        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name="automotive_knowledge"
        )
        
        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.RAG_CHUNK_SIZE,
            chunk_overlap=config.RAG_CHUNK_OVERLAP,
            length_function=len,
        )

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the knowledge base.
        
        Args:
            documents: List of Document objects to add
        """
        # Split documents into chunks
        chunks = self.text_splitter.split_documents(documents)
        
        # Add to vector store
        self.vector_store.add_documents(chunks)

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> None:
        """Add raw texts to the knowledge base.
        
        Args:
            texts: List of text strings
            metadatas: Optional list of metadata dicts for each text
        """
        # Split texts into chunks
        chunks = self.text_splitter.create_documents(texts, metadatas=metadatas)
        
        # Add to vector store
        self.vector_store.add_documents(chunks)

    def retrieve(
        self, 
        query: str, 
        k: int = None,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """Retrieve relevant documents from the knowledge base.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            filter_dict: Optional metadata filter
            
        Returns:
            List of relevant documents
        """
        k = k or config.RAG_TOP_K
        
        if filter_dict:
            results = self.vector_store.similarity_search(
                query, k=k, filter=filter_dict
            )
        else:
            results = self.vector_store.similarity_search(query, k=k)
        
        return results

    def retrieve_with_scores(
        self, 
        query: str, 
        k: int = None,
        filter_dict: Optional[Dict] = None
    ) -> List[Tuple[Document, float]]:
        """Retrieve relevant documents with relevance scores.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            filter_dict: Optional metadata filter
            
        Returns:
            List of tuples (document, score)
        """
        k = k or config.RAG_TOP_K
        
        if filter_dict:
            results = self.vector_store.similarity_search_with_score(
                query, k=k, filter=filter_dict
            )
        else:
            results = self.vector_store.similarity_search_with_score(query, k=k)
        
        return results

    def reflect_on_retrieval(
        self, 
        query: str, 
        retrieved_docs: List[Document],
        threshold: float = None
    ) -> Tuple[bool, float, str]:
        """Reflect on the quality of retrieved documents.
        
        This implements the "Reflect" part of Retrieve-Reflect-Retry.
        
        Args:
            query: Original search query
            retrieved_docs: Documents retrieved
            threshold: Relevance score threshold
            
        Returns:
            Tuple of (is_sufficient, avg_score, reflection_message)
        """
        threshold = threshold or config.REFLECTION_SCORE_THRESHOLD
        
        if not retrieved_docs:
            return False, 0.0, "No documents retrieved. Consider reformulating query or using web search."
        
        # Get documents with scores
        docs_with_scores = self.retrieve_with_scores(query, k=len(retrieved_docs))
        
        if not docs_with_scores:
            return False, 0.0, "Unable to score documents."
        
        # Calculate average relevance score
        # Note: Chroma returns distance, lower is better. Convert to similarity.
        scores = [1 / (1 + score) for _, score in docs_with_scores]
        avg_score = sum(scores) / len(scores)
        
        # Check if retrieval is sufficient
        is_sufficient = avg_score >= threshold
        
        if is_sufficient:
            reflection = f"Retrieved {len(retrieved_docs)} relevant documents with average score {avg_score:.2f}. Sufficient for analysis."
        else:
            reflection = f"Retrieved documents have low relevance (avg score: {avg_score:.2f}). Consider web search or query reformulation."
        
        return is_sufficient, avg_score, reflection

    def initialize_with_sample_data(self) -> None:
        """Initialize the knowledge base with sample automotive data."""
        
        # OBD2 Diagnostic Trouble Codes
        obd2_codes = [
            {
                "text": "C0561 - System Disabled Information Stored. This code indicates that the ABS system has been disabled and the information has been stored in the control module memory. Common causes include faulty wheel speed sensors, damaged wiring, or control module issues. Check wheel speed sensors and wiring connections.",
                "metadata": {"type": "dtc", "system": "chassis", "code": "C0561"}
            },
            {
                "text": "C0750 - Tire Pressure Monitor Sensor Battery Low. This diagnostic code indicates that one or more TPMS (Tire Pressure Monitoring System) sensors have a low battery. The TPMS sensor batteries typically last 5-10 years. When this code appears, the affected sensor(s) need to be replaced. The tire pressure should also be checked and adjusted to manufacturer specifications.",
                "metadata": {"type": "dtc", "system": "chassis", "code": "C0750"}
            },
            {
                "text": "P0420 - Catalyst System Efficiency Below Threshold (Bank 1). This code indicates that the catalytic converter is not operating efficiently. Common causes include a failing catalytic converter, oxygen sensor issues, exhaust leaks, or engine misfires. Diagnosis should include checking oxygen sensor readings and exhaust system inspection.",
                "metadata": {"type": "dtc", "system": "engine", "code": "P0420"}
            },
            {
                "text": "P0301 - Cylinder 1 Misfire Detected. This code indicates that cylinder 1 is experiencing misfires. Common causes include faulty spark plugs, ignition coils, fuel injectors, low compression, or vacuum leaks. Start diagnosis with spark plug and ignition coil inspection.",
                "metadata": {"type": "dtc", "system": "engine", "code": "P0301"}
            },
        ]
        
        # Tire Pressure Information
        tire_info = [
            {
                "text": "Proper tire pressure is critical for vehicle safety and performance. Underinflated tires can lead to poor handling, increased tire wear, reduced fuel economy, and potential tire failure. Most passenger vehicles require 30-35 PSI. Always check tire pressure when tires are cold. The recommended pressure is found on the driver's door jamb sticker.",
                "metadata": {"type": "maintenance", "category": "tires"}
            },
            {
                "text": "TPMS (Tire Pressure Monitoring System) sensors monitor tire pressure and alert the driver when pressure drops below safe levels. There are two types: direct TPMS (sensors in each tire) and indirect TPMS (using ABS sensors). Direct TPMS sensors have batteries that last 5-10 years and require replacement when depleted.",
                "metadata": {"type": "maintenance", "category": "tpms"}
            },
            {
                "text": "When replacing TPMS sensors, ensure compatibility with your vehicle's make, model, and year. After replacement, sensors must be programmed to the vehicle's system. Tire pressure should be set to manufacturer specifications, typically 32-35 PSI for sedans and 35-40 PSI for SUVs and trucks.",
                "metadata": {"type": "repair", "category": "tpms"}
            },
        ]
        
        # General Maintenance
        maintenance_info = [
            {
                "text": "Regular vehicle maintenance schedule: Oil changes every 3,000-5,000 miles (conventional) or 7,500-10,000 miles (synthetic). Tire rotation every 5,000-7,500 miles. Brake inspection every 10,000 miles. Air filter replacement every 15,000-30,000 miles. Transmission fluid every 30,000-60,000 miles.",
                "metadata": {"type": "maintenance", "category": "general"}
            },
            {
                "text": "Warning signs that require immediate attention: Check engine light, ABS warning light, oil pressure warning, battery warning light, brake warning light, and tire pressure warning light. Never ignore these warnings as they indicate potential safety issues.",
                "metadata": {"type": "safety", "category": "warnings"}
            },
        ]
        
        # Combine all data
        all_texts = []
        all_metadatas = []
        
        for item in obd2_codes + tire_info + maintenance_info:
            all_texts.append(item["text"])
            all_metadatas.append(item["metadata"])
        
        # Add to knowledge base
        self.add_texts(all_texts, all_metadatas)
        print(f"Initialized knowledge base with {len(all_texts)} documents.")

    def get_collection_count(self) -> int:
        """Get the number of documents in the knowledge base.
        
        Returns:
            Number of documents
        """
        return self.vector_store._collection.count()


# Global instance
knowledge_base = AutomotiveKnowledgeBase()

# Initialize with sample data if empty
if knowledge_base.get_collection_count() == 0:
    print("Knowledge base is empty. Initializing with sample data...")
    knowledge_base.initialize_with_sample_data()

