from aiohttp import ClientSession, ContentTypeError


async def request(method: str, url: str, **kwargs):
    async with ClientSession() as session:
        async with session.request(method, url, **kwargs) as response:
            try:
                return await response.json()
            except ContentTypeError:
                return {}


async def get(url: str, **kwargs):
    return await request("GET", url, **kwargs)


async def post(url: str, **kwargs):
    return await request("POST", url, **kwargs)
