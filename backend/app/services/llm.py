import logging
import httpx
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
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, headers=self.headers
        ) as client:
            try:
                response = await client.post(
                    settings.LLM_CHAT_PATH,
                    json={
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
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("reply") or data.get("message") or data.get("content") or str(data)
            except httpx.HTTPStatusError as e:
                logger.error("[LLM] chat() HTTP %s: %s", e.response.status_code, e)
                return "Sorry, the AI mechanic is temporarily unavailable. Please try again in a moment."
            except Exception as e:
                logger.error("[LLM] chat() failed: %s", e)
                return "Sorry, the AI mechanic is temporarily unavailable. Please try again in a moment."

    async def full_report(self, dtc_codes: list, vehicle: dict, language: str = "en") -> dict:
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, headers=self.headers
        ) as client:
            try:
                response = await client.post(
                    settings.LLM_FULL_REPORT_PATH,
                    json={"dtc_codes": dtc_codes, "vehicle": vehicle, "language": language},
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "explanation": data.get("explanation") or data.get("message") or str(data),
                    "urgency": data.get("urgency", "medium"),
                    "estimated_cost_min": data.get("estimated_cost_min"),
                    "estimated_cost_max": data.get("estimated_cost_max"),
                }
            except httpx.HTTPStatusError as e:
                logger.error("[LLM] full_report() HTTP %s: %s", e.response.status_code, e)
                return {
                    "explanation": "Full report generation failed. Please try again later.",
                    "urgency": "medium",
                    "estimated_cost_min": None,
                    "estimated_cost_max": None,
                }
            except Exception as e:
                logger.error("[LLM] full_report() failed: %s", e)
                return {
                    "explanation": "Full report generation failed. Please try again later.",
                    "urgency": "medium",
                    "estimated_cost_min": None,
                    "estimated_cost_max": None,
                }


llm_service = LlmService()
