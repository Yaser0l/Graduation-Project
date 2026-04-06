import os
import sys
# Add parent directory of 'src' to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""FastAPI Microservice for Multi-Agent Mechanic Workflow."""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import re
import logging

import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from openai import APITimeoutError, APIConnectionError, AuthenticationError, RateLimitError
import config

from fastapi import Header, Depends

app = FastAPI(title="CarBrain AI Backend")
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_checks() -> None:
    """Emit provider configuration diagnostics on startup (without leaking secrets)."""
    key_set = bool((config.OPENAI_API_KEY or "").strip())
    base = (config.base_url or "").strip()
    logger.info("LLM provider base_url=%s key_present=%s", base or "<empty>", key_set)

    if not key_set:
        logger.warning("OPENAI_API_KEY is empty. Provider requests will fail with authentication errors.")

    if not base:
        logger.warning("BASE_URL/OPENAI_BASE_URL is empty. Falling back may fail depending on provider setup.")

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


def normalize_urgency(value: Optional[str]) -> str:
    if not value:
        return "medium"
    urgency = str(value).strip().lower()
    allowed = {"low", "medium", "high", "critical"}
    return urgency if urgency in allowed else "medium"


URGENCY_RANK = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


def highest_urgency(values: List[str]) -> str:
    normalized = [normalize_urgency(v) for v in values if v]
    if not normalized:
        return "medium"
    return max(normalized, key=lambda x: URGENCY_RANK.get(x, 1))


def parse_analysis_payload(raw: str) -> Dict[str, Any]:
    """Parse model output into {explanation, urgency, per_code_urgency}; tolerates plain text fallback."""
    text = (raw or "").strip()

    # Preferred: pure JSON response
    try:
        data = json.loads(text)
        per_code = data.get("per_code_urgency") if isinstance(data.get("per_code_urgency"), dict) else {}
        return {
            "explanation": data.get("explanation") or text,
            "urgency": normalize_urgency(data.get("urgency")),
            "per_code_urgency": {k: normalize_urgency(v) for k, v in per_code.items()},
        }
    except Exception:
        pass

    # Tolerate markdown fenced JSON blocks
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, flags=re.IGNORECASE)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            per_code = data.get("per_code_urgency") if isinstance(data.get("per_code_urgency"), dict) else {}
            return {
                "explanation": data.get("explanation") or text,
                "urgency": normalize_urgency(data.get("urgency")),
                "per_code_urgency": {k: normalize_urgency(v) for k, v in per_code.items()},
            }
        except Exception:
            pass

    # Plain text fallback with keyword-based extraction
    lowered = text.lower()
    for label in ("critical", "high", "medium", "low"):
        if re.search(rf"\b{label}\b", lowered):
            return {"explanation": text, "urgency": label, "per_code_urgency": {}}

    return {"explanation": text, "urgency": "medium", "per_code_urgency": {}}

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
            
        llm = ChatOpenAI(model="deepseek-chat", temperature=0.7, timeout=25, max_retries=1, **llm_kwargs)
        
        car_info = f"{request.vehicle.year} {request.vehicle.make} {request.vehicle.model}"
        dtcs = ", ".join(request.dtc_codes)
        
        prompt = (
            "You are an automotive diagnostic assistant. "
            "Analyze the DTC codes and return STRICT JSON with this exact shape: "
            '{"explanation":"...","urgency":"low|medium|high|critical","per_code_urgency":{"CODE":"low|medium|high|critical"}}. '
            "Rules: explanation must be concise (2-3 sentences), practical, and non-alarmist. "
            "Classify each code in per_code_urgency. "
            "If there are multiple codes, overall urgency MUST equal the highest severity among all provided codes. "
            "Urgency must reflect immediate risk and drivability. "
            f"Vehicle: {car_info}. Codes: {dtcs}."
        )
        
        messages = [HumanMessage(content=prompt)]
        response = await asyncio.to_thread(llm.invoke, messages)
        
        parsed = parse_analysis_payload(response.content)
        final_urgency = parsed["urgency"]

        if len(request.dtc_codes) > 1:
            per_code = parsed.get("per_code_urgency") or {}
            if per_code:
                picked = [per_code.get(code, "medium") for code in request.dtc_codes]
                final_urgency = highest_urgency(picked + [final_urgency])

        return {
            "explanation": parsed["explanation"],
            "urgency": final_urgency,
        }
    except APITimeoutError:
        dtcs = ", ".join(request.dtc_codes)
        logger.warning("analyze_dtc timed out while calling provider for codes: %s", dtcs)
        return {
            "explanation": f"AI provider timeout. Preliminary result only: detected DTC codes {dtcs}. Please retry when connectivity is stable.",
            "urgency": "medium"
        }
    except APIConnectionError as e:
        dtcs = ", ".join(request.dtc_codes)
        logger.warning("analyze_dtc connection failure base_url=%s err=%s", config.base_url, e)
        return {
            "explanation": f"AI provider connection failed (cannot reach model endpoint). Detected DTC codes: {dtcs}. Check internet/firewall/VPN and BASE_URL.",
            "urgency": "medium"
        }
    except AuthenticationError as e:
        dtcs = ", ".join(request.dtc_codes)
        logger.warning("analyze_dtc auth failure err=%s", e)
        return {
            "explanation": f"AI provider authentication failed (invalid/expired API key). Detected DTC codes: {dtcs}. Update OPENAI_API_KEY and retry.",
            "urgency": "medium"
        }
    except RateLimitError as e:
        dtcs = ", ".join(request.dtc_codes)
        logger.warning("analyze_dtc rate limited err=%s", e)
        return {
            "explanation": f"AI provider rate limit/quota reached. Detected DTC codes: {dtcs}. Retry later or check provider quota.",
            "urgency": "medium"
        }
    except Exception as e:
        logger.warning("analyze_dtc failed (%s): %s", type(e).__name__, e)
        dtcs = ", ".join(request.dtc_codes)
        return {
            "explanation": f"LLM provider temporarily unavailable. Raw DTC codes: {dtcs}. Please retry shortly.",
            "urgency": "medium"
        }

@app.post("/api/llm/full-report", dependencies=[Depends(verify_internal_secret)])
async def full_report(request: AnalyzeRequest):
    """Generates the full comprehensive diagnostic report using the Multi-Agent Workflow."""
    try:
        # Lazy import to avoid loading the full graph + embeddings for lightweight analyze/chat routes.
        from src.main import prepare_input
        from src.graph.main_graph import main_workflow

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
        llm = ChatOpenAI(model="deepseek-chat", temperature=0.7, timeout=25, max_retries=1, **llm_kwargs)
        
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
    except APITimeoutError:
        logger.warning("chat_with_mechanic timed out while calling provider")
        return {
            "reply": "The AI mechanic request timed out due to network/provider delay. Please try again in a moment."
        }
    except APIConnectionError as e:
        logger.warning("chat_with_mechanic connection failure base_url=%s err=%s", config.base_url, e)
        return {
            "reply": "The AI mechanic endpoint is unreachable right now. Check internet/firewall/VPN and provider base URL."
        }
    except AuthenticationError as e:
        logger.warning("chat_with_mechanic auth failure err=%s", e)
        return {
            "reply": "AI provider authentication failed. Please verify your API key and try again."
        }
    except RateLimitError as e:
        logger.warning("chat_with_mechanic rate limited err=%s", e)
        return {
            "reply": "AI provider quota/rate limit reached. Please retry later."
        }
    except Exception as e:
        logger.warning("chat_with_mechanic failed (%s): %s", type(e).__name__, e)
        return {
            "reply": "I am temporarily unable to reach the AI provider. Please try again in a moment."
        }

if __name__ == "__main__":
    # Keep reload opt-in in local dev to avoid double-process cold starts.
    use_reload = os.getenv("UVICORN_RELOAD", "0").strip().lower() in {"1", "true", "yes", "on"}
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=use_reload)
