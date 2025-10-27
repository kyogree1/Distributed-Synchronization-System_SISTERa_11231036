import aiohttp
from typing import Any

class Messenger:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def post_json(self, url: str, path: str, payload: dict[str, Any]):
        async with self.session.post(f"{url}{path}", json=payload, timeout=5) as r:
            return await r.json()

    async def get_json(self, url: str, path: str):
        async with self.session.get(f"{url}{path}", timeout=5) as r:
            return await r.json()
