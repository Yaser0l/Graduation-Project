import asyncio
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class SseService:
    """Manages SSE subscriptions keyed by user_id (str)."""

    def __init__(self):
        # user_id (str) -> set of asyncio.Queue instances
        self.connected_clients: Dict[str, Set[asyncio.Queue]] = {}

    async def subscribe(self, user_id: str):
        queue: asyncio.Queue = asyncio.Queue()
        self.connected_clients.setdefault(user_id, set()).add(queue)
        logger.debug("[SSE] Client connected for user %s", user_id)
        try:
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            clients = self.connected_clients.get(user_id, set())
            clients.discard(queue)
            if not clients:
                self.connected_clients.pop(user_id, None)
            logger.debug("[SSE] Client disconnected for user %s", user_id)
            raise

    async def broadcast_to_user(self, user_id: str, data: dict):
        queues = self.connected_clients.get(user_id)
        if queues:
            event = {"event": "diagnostic:new", "data": data}
            for queue in list(queues):
                await queue.put(event)
            logger.info("[SSE] Broadcast to user %s (%d clients)", user_id, len(queues))


sse_service = SseService()


async def on_report_created(user_id: str, report: dict):
    await sse_service.broadcast_to_user(user_id, report)
