"""FastAPI Microservice for Multi-Agent Mechanic Workflow."""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.main import prepare_input
from src.graph.main_graph import main_workflow
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

app = FastAPI(title="CarBrain AI Backend")

# -----------------
# Pydantic Models
# -----------------
class Vehicle(BaseModel):
    make: Optional[str] = "Unknown"
    model: Optional[str] = "Unknown"
    year: Optional[int] = 2000
    mileage: Optional[int] = 0
    last_oil_change_km: Optional[int] = None

class AnalyzeRequest(BaseModel):
    dtc_codes: List[str]
    vehicle: Vehicle

class ReportModel(BaseModel):
    dtc_codes: List[str]
    explanation: str
    urgency: Optional[str] = "medium"
    estimated_cost_min: Optional[int] = None
    estimated_cost_max: Optional[int] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    report: ReportModel
    vehicle: Vehicle
    history: List[ChatMessage] = []
    message: str

# -----------------
# Endpoints
# -----------------
@app.post("/api/llm/analyze")
async def analyze_dtc(request: AnalyzeRequest):
    """Generates the full diagnostic report using the Multi-Agent Workflow."""
    try:
        # 1. Format the request to match the expected state of our LangGraph workflow
        obd_codes = [{"code": code, "description": "Unknown", "system": "Unknown"} for code in request.dtc_codes]
        
        input_data = {
            "user_id": "api_user",
            "car_metadata": {
                "car_name": request.vehicle.make,
                "car_model": request.vehicle.model,
                "year": request.vehicle.year,
                "mileage": request.vehicle.mileage,
                "vin": ""
            },
            "obd2_data": {
                "diagnostic_codes": obd_codes
            }
        }
        
        # 2. Run the LangGraph Workflow
        state = prepare_input(input_data)
        result = main_workflow.invoke(state)
        
        final_report = result.get("final_report", "Analysis could not be completed.")
        
        # 3. Return the report in the exact format your Node.js backend expects
        return {
            "explanation": final_report,
            "urgency": "medium", # Could use an agent to determine this
            "estimated_cost_min": 100, # Could use an agent to scrape exact costs
            "estimated_cost_max": 500
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/llm/chat")
async def chat_with_mechanic(request: ChatRequest):
    """Handles continuous conversation regarding a previous diagnostic report."""
    try:
        # A lightweight ChatOpenAI tool to answer conversational questions
        # Using the actual generated report as the System Context.
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        system_prompt = f"""You are a helpful, professional automotive mechanic assisting a customer.
You have already provided them with the following diagnostic report:

VEHICLE: {request.vehicle.year} {request.vehicle.make} {request.vehicle.model}
DIAGNOSTIC CODES: {', '.join(request.report.dtc_codes)}

REPORT EXPLANATION:
{request.report.explanation}

Answer their questions specifically based on this report. Keep answers clear and supportive."""

        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history
        for msg in request.history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))
                
        # Add current user message
        messages.append(HumanMessage(content=request.message))
        
        # Generate reply
        response = llm.invoke(messages)
        
        return {
            "reply": response.content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=5000, reload=True)
