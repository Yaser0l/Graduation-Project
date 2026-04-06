import os
import sys
# Add parent directory of 'src' to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""FastAPI Microservice for Multi-Agent Mechanic Workflow."""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

import asyncio
from src.main import prepare_input
from src.graph.main_graph import main_workflow
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import config

from fastapi import Header, Depends

app = FastAPI(title="CarBrain AI Backend")

# -----------------
# Security (Internal Handshake)
# -----------------
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET")

async def verify_internal_secret(x_internal_secret: str = Header(None)):
    if x_internal_secret != INTERNAL_API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Internal Secret")
    return x_internal_secret

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
@app.post("/api/llm/analyze", dependencies=[Depends(verify_internal_secret)])
async def analyze_dtc(request: AnalyzeRequest):
    """Generates a lightning-fast brief explanation of the DTCs."""
    try:
        # Fast single LLM call for immediate database saving
        llm_kwargs = {"api_key": config.OPENAI_API_KEY}
        if config.base_url:
            llm_kwargs["base_url"] = config.base_url
            
        llm = ChatOpenAI(model="deepseek-chat", temperature=0.7, **llm_kwargs)
        
        car_info = f"{request.vehicle.year} {request.vehicle.make} {request.vehicle.model}"
        dtcs = ", ".join(request.dtc_codes)
        
        prompt = f"You are a quick automotive diagnostic assistant. Provide a highly concise, 2-3 sentence brief explanation for the provided DTC codes. Be simple and to the point. Vehicle: {car_info}. Codes: {dtcs}."
        
        messages = [HumanMessage(content=prompt)]
        response = await asyncio.to_thread(llm.invoke, messages)
        
        return {
            "explanation": response.content,
            "urgency": "medium"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/llm/full-report", dependencies=[Depends(verify_internal_secret)])
async def full_report(request: AnalyzeRequest):
    """Generates the full comprehensive diagnostic report using the Multi-Agent Workflow."""
    try:
        # 1. Format the request to match the expected state of our LangGraph workflow
        obd_codes = [{"code": code, "description": "Unknown", "system": "Unknown"} for code in request.dtc_codes]
        
        input_data = {
            "user_id": "api_user",
            "car_metadata": {
                "car_name": request.vehicle.make or "Unknown",
                "car_model": request.vehicle.model or "Unknown",
                "year": request.vehicle.year or 2000,
                "mileage": request.vehicle.mileage,
                "vin": ""
            },
            "obd2_data": {
                "diagnostic_codes": obd_codes
            }
        }
        
        # 2. Run the LangGraph Workflow (this takes ~60-240 seconds)
        state = prepare_input(input_data)
        result = await asyncio.to_thread(main_workflow.invoke, state)
        
        final_report = result.get("final_report", "Analysis could not be completed.")
        
        return {
            "explanation": final_report,
            "urgency": "medium",
            "estimated_cost_min": 100, 
            "estimated_cost_max": 500
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/llm/chat", dependencies=[Depends(verify_internal_secret)])
async def chat_with_mechanic(request: ChatRequest):
    """Handles continuous conversation regarding a previous diagnostic report."""
    try:
        # A lightweight ChatOpenAI tool to answer conversational questions
        # Using the actual generated report as the System Context.
        llm_kwargs = {"api_key": config.OPENAI_API_KEY}
        if config.base_url:
            llm_kwargs["base_url"] = config.base_url
        llm = ChatOpenAI(model="deepseek-chat", temperature=0.7, **llm_kwargs)
        
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
        response = await asyncio.to_thread(llm.invoke, messages)
        
        return {
            "reply": response.content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
