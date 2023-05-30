from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from digiseller.api import Digiseller
from typing import Optional

from digiseller.types.message import Message


class Chat:
    def __init__(self, id_i: int, email: str, product: str, last_date: str, cnt_msg: int, cnt_new: int,
                 digiseller: Digiseller):
        """
        Класс для представления чата в сервисе Digiseller.

        :param id_i: Номер заказа
        :type id_i: int
        :param email: Email покупателя
        :type email: str
        :param product: Название товара
        :type product: str
        :param last_date: Дата и время последнего сообщения
        :type last_date: str
        :param cnt_msg: Количество сообщений
        :type cnt_msg: int
        :param cnt_new: Количество непрочитанных сообщений
        :type cnt_new: int
        :param digiseller: Объект для взаимодействия с API Digiseller
        :type digiseller: Digiseller

        :ivar id_i: Номер заказа
        :vartype id_i: int
        :ivar email: Email покупателя
        :vartype email: str
        :ivar product: Название товара
        :vartype product: str
        :ivar last_date: Дата и время последнего сообщения
        :vartype last_date: str
        :ivar cnt_msg: Количество сообщений
        :vartype cnt_msg: int
        :ivar cnt_new: Количество непрочитанных сообщений
        :vartype cnt_new: int
        :ivar digiseller: Объект для взаимодействия с API Digiseller
        :vartype digiseller: Digiseller
        """
        self.id_i = id_i
        self.email = email
        self.product = product
        self.last_date = last_date
        self.cnt_msg = cnt_msg
        self.cnt_new = cnt_new
        self.digiseller = digiseller

    @classmethod
    def from_dict(cls, data: dict, digiseller: Digiseller):
        """
        Создание объекта `Chat` из словаря.

        :param data: Данные чата
        :type data: dict
        :param digiseller: Объект для взаимодействия с API Digiseller
        :type digiseller: Digiseller
        :return: Объект чата
        :rtype: Chat
        """
        return cls(
            id_i=data['id_i'],
            email=data['email'],
            product=data['product'],
            last_date=data['last_date'],
            cnt_msg=data['cnt_msg'],
            cnt_new=data['cnt_new'],
            digiseller=digiseller,
        )

    async def send_message(self, message: str):
        """
        Отправка сообщения в чат.

        :param message: Сообщение для отправки
        :type message: str
        """
        await self.digiseller.send_message(self.id_i, message)

    async def get_messages(self, newer: Optional[int] = None) -> list[Message]:
        """
        Получение сообщений чата.

        :param newer: Опциональный параметр для фильтрации сообщений
        :type newer: Optional[int]
        :return: Список сообщений
        :rtype: list[Message]
        """
        return await self.digiseller.get_messages(self.id_i, newer)
