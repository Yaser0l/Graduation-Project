import os
import sys
# Add parent directory of 'src' to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""FastAPI Microservice for Multi-Agent Mechanic Workflow."""
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
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

    # Pre-load the embedding model at startup so RAG queries are not delayed by model download
    try:
        from src.rag.knowledge_base import knowledge_base
        _ = knowledge_base.embeddings  # triggers model download + cache
        logger.info("Embedding model pre-loaded successfully")
    except Exception as e:
        logger.warning("Could not pre-load embedding model: %s. RAG will load it lazily on first call.", e)

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
    language: Optional[str] = "en"
    stream_mode: Optional[str] = "word"
    stream_chunk_size: Optional[int] = 3

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
    stream_mode: Optional[str] = "word"
    stream_chunk_size: Optional[int] = 3


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text_part = item.get("text")
                if text_part:
                    parts.append(str(text_part))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return str(content)


def _normalize_stream_mode(mode: Optional[str]) -> str:
    normalized = (mode or "word").strip().lower()
    return normalized if normalized in {"word", "char"} else "word"


def _chunk_text(text: str, mode: str = "word", chunk_size: int = 1):
    if not text:
        return
    if mode == "char":
        tokens = list(text)
    else:
        tokens = re.findall(r"\S+\s*|\s+", text)
    size = max(1, int(chunk_size or 1))
    for idx in range(0, len(tokens), size):
        yield "".join(tokens[idx: idx + size])


def _ndjson(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


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
def _build_dtc_query(dtc_codes: List[str]) -> str:
    """Build a RAG query string from DTC codes."""
    return f"OBD2 diagnostic codes {' '.join(dtc_codes)} causes repair solutions"


@app.post("/api/llm/analyze", dependencies=[Depends(verify_internal_secret)])
async def analyze_dtc(request: AnalyzeRequest):
    """Generates a brief explanation of the DTCs using RAG knowledge first, with plain LLM fallback."""
    try:
        # Step 1: Query the RAG knowledge base (no Tavily web search)
        rag_context = ""
        rag_sources = False
        try:
            from src.tools.rag_tool import retrieve_with_reflection

            query = _build_dtc_query(request.dtc_codes)
            logger.info("analyze_dtc querying RAG for codes: %s", ", ".join(request.dtc_codes))
            retrieval = retrieve_with_reflection.invoke({"query": query, "top_k": 3})
            rag_sources = retrieval.get("is_sufficient", False)
            rag_content = retrieval.get("content", "").strip()

            if rag_content:
                logger.info(
                    "analyze_dtc RAG returned %d documents (score=%.2f, sufficient=%s)",
                    retrieval.get("document_count", 0),
                    retrieval.get("score", 0.0),
                    rag_sources,
                )
                rag_context = f"\nREFERENCE INFORMATION:\n{rag_content}\n"
            else:
                logger.info("analyze_dtc RAG returned no content — falling back to plain LLM")
        except Exception as rag_err:
            logger.warning("analyze_dtc RAG retrieval failed (%s), falling back to plain LLM", rag_err)

        # Step 2: Build the LLM call (with RAG context if available, otherwise plain)
        llm_kwargs = {"api_key": config.OPENAI_API_KEY}
        if config.base_url:
            llm_kwargs["base_url"] = config.base_url

        llm = ChatOpenAI(model="deepseek-chat", temperature=0.7, timeout=240, max_retries=1, **llm_kwargs)

        car_info = f"{request.vehicle.year} {request.vehicle.make} {request.vehicle.model}"
        dtcs = ", ".join(request.dtc_codes)

        if rag_context:
            prompt = (
                "You are an automotive diagnostic assistant. "
                "Analyze the DTC codes using the reference information below. "
                "Return STRICT JSON with this exact shape: "
                '{"explanation":"...","urgency":"low|medium|high|critical","per_code_urgency":{"CODE":"low|medium|high|critical"}}. '
                "Rules: explanation must be concise (2-3 sentences), practical, and non-alarmist. "
                "Classify each code in per_code_urgency. "
                "If there are multiple codes, overall urgency MUST equal the highest severity among all provided codes. "
                "Urgency must reflect immediate risk and drivability. "
                f"Vehicle: {car_info}. Codes: {dtcs}."
                f"{rag_context}"
            )
        else:
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
            "rag_sources_used": rag_sources,
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
    """Generates and streams a comprehensive diagnostic report using the Multi-Agent Workflow."""
    stream_mode = _normalize_stream_mode(request.stream_mode)
    stream_chunk_size = max(1, min(int(request.stream_chunk_size or 3), 12))
    is_arabic = str(request.language or "en").strip().lower().startswith("ar")

    start_msg = (
        "بدء مسار التشخيص...\nقد يستغرق ذلك من 3 إلى 5 دقائق.\n\n"
        if is_arabic
        else "Starting diagnostic pipeline...\nThis may take 3-5 minutes.\n\n"
    )
    running_obd_msg = "جاري تحليل بيانات OBD2...\n\n" if is_arabic else "Running OBD2 analysis...\n\n"
    composing_msg = "جاري إنشاء التقرير النهائي بصيغة سهلة القراءة...\n\n" if is_arabic else "Generating final user-friendly report...\n\n"

    async def event_stream():
        try:
            # Lazy imports keep analyze/chat fast.
            from src.main import prepare_input
            from src.orchestrations.obd2_orchestration import obd2_orchestration
            from src.orchestrations.writer_orchestration import writer_orchestration

            yield _ndjson({"event": "start"})
            yield _ndjson({"event": "token", "chunk": start_msg})

            obd_codes = [{"code": code, "description": "Unknown", "system": "Unknown"} for code in request.dtc_codes]
            input_data = {
                "user_id": "api_user",
                "language": request.language or "en",
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

            state = prepare_input(input_data)

            yield _ndjson({"event": "token", "chunk": running_obd_msg})
            obd2_state = {
                "user_id": state["user_id"],
                "car_metadata": state["car_metadata"],
                "obd2_data": state["obd2_data"],
                "retrieved_context": [],
                "web_search_results": None,
                "analysis_draft": None,
                "analysis_review": None,
                "final_analysis": None,
                "reflection_count": 0,
                "revision_count": 0,
                "messages": state.get("messages", []),
            }
            obd2_result = await asyncio.to_thread(obd2_orchestration.invoke, obd2_state)
            obd2_analysis = obd2_result.get("final_analysis") or obd2_result.get("analysis_draft") or ""

            if obd2_analysis:
                pass

            writer_state = {
                "user_id": state["user_id"],
                "language": state.get("language", "en"),
                "car_metadata": state["car_metadata"],
                "obd2_analysis": obd2_analysis,
                "product_recommendations": None,
                "draft_report": None,
                "technical_review": None,
                "user_friendly_report": None,
                "final_report": "",
                "messages": state.get("messages", []),
            }

            yield _ndjson({"event": "token", "chunk": composing_msg})
            writer_result = await asyncio.to_thread(writer_orchestration.invoke, writer_state)
            final_report = writer_result.get("final_report") or "Analysis could not be completed."

            for chunk in _chunk_text(final_report, mode=stream_mode, chunk_size=stream_chunk_size):
                yield _ndjson({"event": "token", "chunk": chunk})
                await asyncio.sleep(0)

            yield _ndjson(
                {
                    "event": "done",
                    "explanation": final_report,
                    "urgency": "medium",
                    "estimated_cost_min": 100,
                    "estimated_cost_max": 500,
                }
            )
        except Exception as e:
            logger.exception("full_report streaming failed")
            yield _ndjson({"event": "error", "message": str(e)})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/api/llm/chat", dependencies=[Depends(verify_internal_secret)])
async def chat_with_mechanic(request: ChatRequest):
    """Handles continuous conversation and streams model tokens in real time."""
    async def event_stream():
        try:
            llm_kwargs = {"api_key": config.OPENAI_API_KEY}
            if config.base_url:
                llm_kwargs["base_url"] = config.base_url
            llm = ChatOpenAI(model="deepseek-chat", temperature=0.7, timeout=60, max_retries=1, **llm_kwargs)

            system_prompt = f"""You are a helpful, professional automotive mechanic assisting a customer.
You have already provided them with the following diagnostic report:

VEHICLE: {request.vehicle.year} {request.vehicle.make} {request.vehicle.model}
DIAGNOSTIC CODES: {', '.join(request.report.dtc_codes)}

REPORT EXPLANATION:
{request.report.explanation}

Answer their questions specifically based on this report. Keep answers clear and supportive."""

            messages = [SystemMessage(content=system_prompt)]
            for msg in request.history:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                else:
                    messages.append(AIMessage(content=msg.content))
            messages.append(HumanMessage(content=request.message))

            mode = _normalize_stream_mode(request.stream_mode)
            size = max(1, min(int(request.stream_chunk_size or 3), 12))

            yield _ndjson({"event": "start"})
            response_parts: List[str] = []

            async for chunk in llm.astream(messages):
                piece = _content_to_text(getattr(chunk, "content", ""))
                if not piece:
                    continue
                response_parts.append(piece)
                for out in _chunk_text(piece, mode=mode, chunk_size=size):
                    yield _ndjson({"event": "token", "chunk": out})

            full_reply = "".join(response_parts).strip()
            yield _ndjson({"event": "done", "reply": full_reply})
        except APITimeoutError:
            yield _ndjson({
                "event": "error",
                "message": "The AI mechanic request timed out due to network/provider delay. Please try again in a moment."
            })
        except APIConnectionError:
            yield _ndjson({
                "event": "error",
                "message": "The AI mechanic endpoint is unreachable right now. Check internet/firewall/VPN and provider base URL."
            })
        except AuthenticationError:
            yield _ndjson({
                "event": "error",
                "message": "AI provider authentication failed. Please verify your API key and try again."
            })
        except RateLimitError:
            yield _ndjson({
                "event": "error",
                "message": "AI provider quota/rate limit reached. Please retry later."
            })
        except Exception as e:
            logger.warning("chat_with_mechanic failed (%s): %s", type(e).__name__, e)
            yield _ndjson({
                "event": "error",
                "message": "I am temporarily unable to reach the AI provider. Please try again in a moment."
            })

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")

if __name__ == "__main__":
    # Keep reload opt-in in local dev to avoid double-process cold starts.
    use_reload = os.getenv("UVICORN_RELOAD", "0").strip().lower() in {"1", "true", "yes", "on"}
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=use_reload)
