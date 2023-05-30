import hashlib
import json
import time
from datetime import datetime
from typing import Optional

import aiofiles
import aiofiles.os
import aiohttp
import pytz
from aiohttp import ContentTypeError
from dateutil.relativedelta import relativedelta
from yarl import URL

from digiseller.errors import APIHTTPError
from digiseller.types.chat import Chat
from digiseller.types.message import Message


class Digiseller:
    """
    Класс для работы с API Digiseller.

    :param seller_id: идентификатор продавца
    :param seller_api_key: API ключ продавца
    """
    ENDPOINT = 'https://api.digiseller.ru/api'  # Конечная точка API

    def __init__(self, seller_id: int, seller_api_key: str):
        """
        Конструктор класса.

        :param seller_id: идентификатор продавца
        :param seller_api_key: API ключ продавца
        """
        self.seller_id = seller_id
        self.seller_api_key = seller_api_key
        self.token: Optional[dict] = None

    async def read_token(self) -> dict | None:
        """
        Чтение токена из файла.

        :return: Токен в виде словаря или None, если файл не найден.
        """
        try:
            # Открытие файла для чтения токена
            async with aiofiles.open(f'.cache/{self.seller_id}', 'r') as f:
                return json.loads(await f.read())
        except FileNotFoundError:
            return None

    async def write_token(self, token: dict):
        """
        Запись токена в файл.

        :param token: токен, который нужно записать в файл
        """
        try:
            # Создание каталога для кеша, если его нет
            await aiofiles.os.mkdir('.cache')
        except FileExistsError:
            pass
        # Открытие файла для записи токена
        async with aiofiles.open(f'.cache/{self.seller_id}', 'w') as f:
            await f.write(json.dumps(token))

    async def request(self, method: str, path: str, auth=True, json: Optional[dict] = None, **params):
        """
        Асинхронная функция для выполнения запросов к API.

        :param method: HTTP метод (например, 'GET' или 'POST')
        :param path: путь к API
        :param auth: если True, то будет произведена попытка авторизации
        :param params: параметры запроса
        :return: ответ от сервера
        """
        # Формирование URL
        url = URL(self.ENDPOINT + path)
        # Если нужна авторизация
        if auth:
            # Обновляем токен при необходимости
            params['token'] = await self.rotate_token()  # Добавляем токен в параметры запроса

        for key in list(params.keys()):
            if params[key] is None:
                del params[key]
        # Отправка запроса к серверу
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, params=params, json=json) as response:
                # Проверка на успешность ответа
                if str(response.status)[0] == '2':
                    try:
                        response_json = await response.json()
                        return response_json
                    except ContentTypeError:
                        print('ContentTypeError')
                else:
                    text = await response.text() or str(response.url)
                    raise APIHTTPError(f'{response.status} | {response.url} | ' + text)

    async def post(self, *args, **kwargs) -> dict:
        return await self.request('post', *args, **kwargs)

    async def get(self, *args, **kwargs) -> dict:
        return await self.request('get', *args, **kwargs)

    async def get_auth_token(self) -> dict:
        """
        Получение токена авторизации от API.

        :return: Токен авторизации в виде словаря
        """
        timestamp = int(time.time())
        data_to_hash = f"{self.seller_api_key}{timestamp}".encode('utf-8')

        # Создание хеша для подписи
        hasher = hashlib.sha256()
        hasher.update(data_to_hash)
        sign = hasher.hexdigest()

        # Отправка запроса для получения токена
        return await self.post('/apilogin', auth=False,
                               json=dict(
                                   seller_id=self.seller_id,
                                   timestamp=timestamp,
                                   sign=sign
                               ))

    async def rotate_token(self) -> str:
        """
        Асинхронная функция для обновления токена авторизации.

        Проверяет существование текущего токена, если его нет, пытается прочитать его из файла.
        Если и в файле токена нет, получает новый токен и записывает его в файл.
        Затем проверяет, не истекло ли время действия токена, и если это так, получает и записывает новый токен.
        """
        # Проверка наличия токена
        if not self.token:
            self.token = await self.read_token()
            # Проверка наличия токена в файле
            if not self.token:
                self.token = await self.get_auth_token()  # Получение нового токена
                await self.write_token(self.token)  # Запись токена в файл

        # Получение даты истечения срока действия токена
        timestamp_str = self.token['valid_thru']
        timestamp_str = timestamp_str[:-1][:19] + timestamp_str[-1]
        valid_until = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')
        # Проверка, не истекло ли время действия токена
        if valid_until <= datetime.utcnow():
            print('not valid')
            self.token = await self.get_auth_token()  # Получение нового токена
            await self.write_token(self.token)  # Запись токена в файл
        return self.token['token']

    async def get_messages(self, id_i: int, newer: Optional[int] = None) -> list[Message]:
        data = await self.get('/debates/v2', id_i=id_i, newer=newer)
        await self.set_chat_seen(id_i)
        return [Message.from_dict(item) for item in data]

    async def get_chats(self, filter_new: Optional[int] = None, email: Optional[str] = None,
                        id_ds: Optional[int] = None) -> list[Chat]:
        data = await self.get('/debates/v2/chats',
                              filter_new=filter_new,
                              email=email,
                              id_ds=id_ds)
        return [Chat.from_dict(chat, self) for chat in data['chats']]

    async def send_message(self, id_i: int, message: str):
        return await self.post('/debates/v2/', json=dict(message=message), id_i=id_i)

    async def set_chat_seen(self, id_i: int):
        return await self.post('/debates/v2/seen', id_i=id_i)

    async def get_sells(self, rows=10, date_start=None):

        # Создаем объект часового пояса для Москвы
        moscow_tz = pytz.timezone('Europe/Moscow')

        # Получаем текущую дату и время в этом часовом поясе
        current_datetime = datetime.now(moscow_tz)

        # Форматируем строку согласно требуемому формату
        date_finish = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
        date_start = date_start or (current_datetime - relativedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')

        return await self.post('/seller-sells/v2', json=dict(rows=rows,
                                                             date_start=date_start,
                                                             date_finish=date_finish))

    async def get_purchase(self, invoice_id: int):
        data = await self.get(f'/purchase/info/{invoice_id}')
        data['content']['invoice_id'] = invoice_id
        return data['content']

    async def get_product(self, product_id: int):
        data = await self.get(f'/products/list',
                              ids=product_id)
        try:
            return data[0]
        except IndexError:
            return None

    async def get_purchase_by_code(self, code: str):
        return await self.get(f'/purchases/unique-code/{code}')
