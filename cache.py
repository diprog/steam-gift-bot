import aiofiles

cache = {}


async def get_last_sells_retrieve_date():
    try:
        async with aiofiles.open('.cache/sells_retrieve_date', 'r') as f:
            return await f.read()
    except FileNotFoundError:
        return None


async def write_last_sells_retrieve_date(date_string: str):
    async with aiofiles.open('.cache/sells_retrieve_date', 'w') as f:
        await f.write(date_string)
