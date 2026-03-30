"""Writer State definition for the workflow."""
from typing import TypedDict, List, Optional, Dict, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
from src.states.obd2_state import CarMetadata


class ProductRecommendation(BaseModel):
    """Product recommendation structure."""
    product_name: str = Field(description="Name of the recommended product")
    product_type: str = Field(description="Type of product (e.g., tire, brake pad)")
    price: Optional[str] = Field(default=None, description="Price information")
    vendor: Optional[str] = Field(default=None, description="Vendor or retailer")
    link: Optional[str] = Field(default=None, description="Product link")
    compatibility: Optional[str] = Field(default=None, description="Compatibility notes")


class WriterState(TypedDict):
    """State for Writer orchestration layer."""
    user_id: str  # User identifier
    car_metadata: CarMetadata  # Car information
    obd2_analysis: str  # Input from OBD2 orchestration
    product_recommendations: Optional[List[Dict]]  # Web search results for products
    draft_report: Optional[str]  # Technical writer output
    technical_review: Optional[str]  # Technical review output
    user_friendly_report: Optional[str]  # Formatted output
    final_report: str  # Final user-facing report
    messages: Annotated[List[BaseMessage], add_messages]  # Message history

