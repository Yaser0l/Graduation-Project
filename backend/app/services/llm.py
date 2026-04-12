import logging
import httpx
import re
import json
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class LlmService:
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL
        self.timeout = 240.0
        self.headers = {
            "Content-Type": "application/json",
            "X-Internal-Secret": settings.INTERNAL_API_SECRET,
        }
        if settings.LLM_API_KEY:
            self.headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

    def chunk_text(self, text: str, mode: str = "word", chunk_size: int = 1):
        if not text:
            return

        normalized_mode = (mode or "word").lower()
        size = max(1, int(chunk_size or 1))

        if normalized_mode == "char":
            tokens = list(text)
        else:
            # Keep spaces attached where possible so reconstruction preserves formatting.
            tokens = re.findall(r"\S+\s*|\s+", text)

        for idx in range(0, len(tokens), size):
            yield "".join(tokens[idx: idx + size])

    async def analyze(self, dtc_codes: List[str], vehicle: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, headers=self.headers
        ) as client:
            try:
                response = await client.post(
                    settings.LLM_ANALYZE_PATH,
                    json={"dtc_codes": dtc_codes, "vehicle": vehicle},
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "explanation": data.get("explanation") or data.get("message") or str(data),
                    "urgency": data.get("urgency", "medium"),
                    "estimated_cost_min": data.get("estimated_cost_min")
                        or (data.get("cost_range") or [None])[0],
                    "estimated_cost_max": data.get("estimated_cost_max")
                        or (data.get("cost_range") or [None, None])[1],
                }
            except httpx.HTTPStatusError as e:
                logger.error("[LLM] analyze() HTTP %s: %s", e.response.status_code, e)
                raise
            except Exception as e:
                logger.error("[LLM] analyze() failed: %s", e)
                return {
                    "explanation": f"LLM service unavailable. Raw DTC codes: {', '.join(dtc_codes)}. Please consult a mechanic.",
                    "urgency": "medium",
                    "estimated_cost_min": None,
                    "estimated_cost_max": None,
                }

    async def chat(
        self,
        report: Dict[str, Any],
        vehicle: Dict[str, Any],
        history: List[Dict[str, str]],
        user_message: str,
    ) -> str:
        reply_text = ""
        async for event in self.chat_stream(
            report=report,
            vehicle=vehicle,
            history=history,
            user_message=user_message,
            stream_mode="word",
            stream_chunk_size=3,
        ):
            if event.get("event") == "done":
                reply_text = event.get("reply") or reply_text
            elif event.get("event") == "token":
                reply_text += event.get("chunk") or ""

        if reply_text:
            return reply_text

        return "Sorry, the AI mechanic is temporarily unavailable. Please try again in a moment."

    async def chat_stream(
        self,
        report: Dict[str, Any],
        vehicle: Dict[str, Any],
        history: List[Dict[str, str]],
        user_message: str,
        stream_mode: str = "word",
        stream_chunk_size: int = 3,
    ):
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, headers=self.headers
        ) as client:
            try:
                payload = {
                        "report": {
                            "dtc_codes": report.get("dtc_codes"),
                            "explanation": report.get("llm_explanation"),
                            "urgency": report.get("urgency"),
                            "estimated_cost_min": report.get("estimated_cost_min"),
                            "estimated_cost_max": report.get("estimated_cost_max"),
                        },
                        "vehicle": {
                            "make": vehicle.get("make"),
                            "model": vehicle.get("model"),
                            "year": vehicle.get("year"),
                            "mileage": vehicle.get("mileage"),
                        },
                        "history": history,
                        "message": user_message,
                        "stream_mode": stream_mode,
                        "stream_chunk_size": stream_chunk_size,
                    }

                async with client.stream("POST", settings.LLM_CHAT_PATH, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        yield payload
            except httpx.HTTPStatusError as e:
                logger.error("[LLM] chat() HTTP %s: %s", e.response.status_code, e)
                yield {
                    "event": "error",
                    "message": "Sorry, the AI mechanic is temporarily unavailable. Please try again in a moment.",
                }
            except Exception as e:
                logger.error("[LLM] chat() failed: %s", e)
                yield {
                    "event": "error",
                    "message": "Sorry, the AI mechanic is temporarily unavailable. Please try again in a moment.",
                }

    async def full_report(self, dtc_codes: list, vehicle: dict, language: str = "en") -> dict:
        result = {
            "explanation": "",
            "urgency": "medium",
            "estimated_cost_min": None,
            "estimated_cost_max": None,
        }
        async for event in self.full_report_stream(
            dtc_codes=dtc_codes,
            vehicle=vehicle,
            language=language,
            stream_mode="word",
            stream_chunk_size=3,
        ):
            if event.get("event") == "token":
                result["explanation"] += event.get("chunk") or ""
            elif event.get("event") == "done":
                result["explanation"] = event.get("explanation") or result["explanation"]
                result["urgency"] = event.get("urgency", "medium")
                result["estimated_cost_min"] = event.get("estimated_cost_min")
                result["estimated_cost_max"] = event.get("estimated_cost_max")
        if result["explanation"]:
            return result
        return {
            "explanation": "Full report generation failed. Please try again later.",
            "urgency": "medium",
            "estimated_cost_min": None,
            "estimated_cost_max": None,
        }

    async def full_report_stream(
        self,
        dtc_codes: list,
        vehicle: dict,
        language: str = "en",
        stream_mode: str = "word",
        stream_chunk_size: int = 3,
    ):
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, headers=self.headers
        ) as client:
            try:
                payload = {
                    "dtc_codes": dtc_codes,
                    "vehicle": vehicle,
                    "language": language,
                    "stream_mode": stream_mode,
                    "stream_chunk_size": stream_chunk_size,
                }
                async with client.stream("POST", settings.LLM_FULL_REPORT_PATH, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        yield payload
            except httpx.HTTPStatusError as e:
                logger.error("[LLM] full_report() HTTP %s: %s", e.response.status_code, e)
                yield {
                    "event": "error",
                    "message": "Full report generation failed. Please try again later.",
                }
            except Exception as e:
                logger.error("[LLM] full_report() failed: %s", e)
                yield {
                    "event": "error",
                    "message": "Full report generation failed. Please try again later.",
                }


llm_service = LlmService()
