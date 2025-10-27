import asyncio
from typing import Callable

class Heartbeat:
    def __init__(self, ping: Callable[[], None], interval_ms: int = 1000):
        self._ping = ping
        self._interval = interval_ms / 1000
        self._task = None

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self._run())

    async def _run(self):
        while True:
            try:
                await self._ping()
            except Exception:
                pass
            await asyncio.sleep(self._interval)
