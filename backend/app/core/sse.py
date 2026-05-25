import asyncio
import logging
import json
from typing import Dict, Set

logger = logging.getLogger(__name__)


class SseService:
    """Manages SSE subscriptions keyed by user_id (str)."""

    def __init__(self):
        # user_id (str) -> set of asyncio.Queue instances
        self.connected_clients: Dict[str, Set[asyncio.Queue]] = {}

    async def subscribe(self, user_id: str, request=None):
        queue: asyncio.Queue = asyncio.Queue()
        self.connected_clients.setdefault(user_id, set()).add(queue)
        logger.debug("[SSE] Client connected for user %s", user_id)
        try:
            while True:
                if request is not None and await request.is_disconnected():
                    logger.debug("[SSE] Client disconnected (detected via request.is_disconnected()) for user %s", user_id)
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield data
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.debug("[SSE] Client connection cancelled for user %s", user_id)
            raise
        finally:
            clients = self.connected_clients.get(user_id, set())
            clients.discard(queue)
            if not clients:
                self.connected_clients.pop(user_id, None)
            logger.debug("[SSE] Client queue cleaned up for user %s", user_id)

    async def broadcast_to_user(self, user_id: str, data: dict, event_type: str = "diagnostic:new"):
        queues = self.connected_clients.get(user_id)
        if queues:
            # Always serialize as JSON so browser-side JSON.parse works reliably.
            event = {"event": event_type, "data": json.dumps(data, default=str)}
            for queue in list(queues):
                await queue.put(event)
            logger.info("[SSE] Broadcast to user %s (%d clients)", user_id, len(queues))


sse_service = SseService()


async def on_report_created(user_id: str, report: dict, event_type: str = "diagnostic:new"):
    await sse_service.broadcast_to_user(user_id, report, event_type=event_type)
