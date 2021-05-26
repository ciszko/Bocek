import aiohttp
import asyncio


async def get_all_data():
    url = 'https://192.168.0.31:29999/liveclientdata/allgamedata'
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with session.get(url, timeout=1) as resp:
            data = await resp.json()
            print(data)

if __name__ == '__main__':
    asyncio.run(get_all_data())
