import os.path
from copy import copy

import aiofiles
import jsonpickle

data_dir_path = os.path.abspath('db/data')
if not os.path.exists(data_dir_path):
    os.mkdir(data_dir_path)

cache = {}


class Storage:
    def __init__(self, filename: str):
        self.filepath = data_dir_path + '/' + filename + '.json'

    async def write(self, obj):
        async with aiofiles.open(self.filepath, 'w', encoding='utf-8') as f:
            cache[self.filepath] = copy(obj)
            await f.write(jsonpickle.encode(obj, keys=True))

    async def read(self, default=None):
        if cache.get(self.filepath):
            return cache[self.filepath]
        try:
            async with aiofiles.open(self.filepath, 'r', encoding='utf-8') as f:
                if cache.get(self.filepath) is not None:
                    return copy(cache[self.filepath])
                obj = jsonpickle.decode(await f.read(), keys=True)
                cache[self.filepath] = obj
                return obj
        except FileNotFoundError:
            return default
