"""OBD2 State definition for the workflow."""
from typing import TypedDict, Dict, Any, List, Optional, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class CarMetadata(BaseModel):
    """Car metadata information."""
    car_model: str = Field(description="Car model (e.g., SE, EX, Limited)")
    car_name: str = Field(description="Car name (e.g., Toyota Camry)")
    mileage: int = Field(description="Current mileage in miles")
    year: int = Field(description="Manufacturing year")
    vin: Optional[str] = Field(default=None, description="Vehicle Identification Number")


class DiagnosticCode(BaseModel):
    """OBD2 diagnostic trouble code."""
    code: str = Field(description="DTC code (e.g., P0420, C0561)")
    description: str = Field(description="Code description")
    system: str = Field(description="Affected system (e.g., Engine, Chassis)")


class SensorReadings(BaseModel):
    """Sensor readings from OBD2."""
    tire_pressure: Optional[Dict[str, Any]] = Field(default=None, description="Tire pressure data")
    engine_temp: Optional[float] = Field(default=None, description="Engine temperature")
    oil_pressure: Optional[float] = Field(default=None, description="Oil pressure")
    battery_voltage: Optional[float] = Field(default=None, description="Battery voltage")


class OBD2Data(BaseModel):
    """Complete OBD2 diagnostic data."""
    diagnostic_codes: List[DiagnosticCode] = Field(description="List of diagnostic trouble codes")
    sensor_readings: SensorReadings = Field(description="Sensor readings")
    freeze_frame_data: Optional[Dict[str, Any]] = Field(default=None, description="Freeze frame data")


class OBD2State(TypedDict):
    """State for OBD2 orchestration layer."""
    user_id: str  # User identifier
    car_metadata: CarMetadata  # Car information
    obd2_data: Dict[str, Any]  # Raw OBD2 codes and sensor data
    retrieved_context: List[str]  # Context retrieved from RAG
    web_search_results: Optional[List[str]]  # Results from web search
    analysis_draft: Optional[str]  # Writer agent output
    analysis_review: Optional[str]  # Observation agent feedback
    final_analysis: Optional[str]  # Approved analysis
    reflection_count: int  # Track Retrieve-Reflect-Retry cycles
    revision_count: int  # Track writer-observer revision cycles
    messages: Annotated[List[BaseMessage], add_messages]  # Message history

