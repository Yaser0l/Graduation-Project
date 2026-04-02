import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings

class LlmService:
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL
        self.api_key = settings.LLM_API_KEY
        self.timeout = 240.0
        self.headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def analyze(self, dtc_codes: List[str], vehicle: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers=self.headers) as client:
            try:
                response = await client.post(settings.LLM_ANALYZE_PATH, json={
                    "dtc_codes": dtc_codes,
                    "vehicle": vehicle
                })
                data = response.json()
                return {
                    "explanation": data.get("explanation") or data.get("message") or str(data),
                    "urgency": data.get("urgency", "medium"),
                    "estimated_cost_min": data.get("estimated_cost_min") or data.get("cost_range", [None])[0],
                    "estimated_cost_max": data.get("estimated_cost_max") or data.get("cost_range", [None, None])[1]
                }
            except Exception as e:
                print(f"[LLM] analyze() failed: {e}")
                return {
                    "explanation": f"LLM service unavailable. Raw DTC codes: {', '.join(dtc_codes)}. Please consult a mechanic.",
                    "urgency": "medium",
                    "estimated_cost_min": None,
                    "estimated_cost_max": None
                }

    async def chat(self, report: Dict[str, Any], vehicle: Dict[str, Any], history: List[Dict[str, str]], user_message: str) -> str:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers=self.headers) as client:
            try:
                response = await client.post(settings.LLM_CHAT_PATH, json={
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
                    "message": user_message
                })
                data = response.json()
                return data.get("reply") or data.get("message") or data.get("content") or str(data)
            except Exception as e:
                print(f"[LLM] chat() failed: {e}")
                return "Sorry, the AI mechanic is temporarily unavailable. Please try again in a moment."

llm_service = LlmService()
