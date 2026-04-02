import asyncio
from typing import Dict, Set
from uuid import UUID
from sse_starlette.sse import EventSourceResponse

class SseService:
    def __init__(self):
        # userId -> Set of asyncio.Queue
        self.connected_clients: Dict[UUID, Set[asyncio.Queue]] = {}

    async def subscribe(self, user_id: UUID):
        queue = asyncio.Queue()
        if user_id not in self.connected_clients:
            self.connected_clients[user_id] = set()
        self.connected_clients[user_id].add(queue)
        
        try:
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            self.connected_clients[user_id].remove(queue)
            if not self.connected_clients[user_id]:
                del self.connected_clients[user_id]
            raise

    async def broadcast_to_user(self, user_id: UUID, data: dict):
        if user_id in self.connected_clients:
            event = {"event": "diagnostic:new", "data": data}
            for queue in self.connected_clients[user_id]:
                await queue.put(event)

sse_service = SseService()

async def on_report_created(user_id: UUID, report: dict):
    await sse_service.broadcast_to_user(user_id, report)
