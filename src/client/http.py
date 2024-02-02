from aiohttp import ClientSession


async def get(url: str, **kwargs):
    async with ClientSession() as session:
        async with session.get(url, **kwargs) as response:
            return await response.json()


async def post(url: str, **kwargs):
    async with ClientSession() as session:
        async with session.post(url, **kwargs) as response:
            return await response.json()
