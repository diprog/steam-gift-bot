import time
from typing import Optional

from db.storage import Storage

storage = Storage('deliveries')


class DeliveryStatus:
    WAITING_UNTIL_DELIVERY = 0
    GETTING_PURCHASE_INFO = 1
    SENDING_FRIEND_INVITE = 2
    AWAITING_FRIEND_INVITATION_ACCEPT = 3
    SENDING_GIFT = 4
    DELIVERED = 5


class Delivery:
    def __init__(self, digiseller_code: str, status: int, delivery_delay: Optional[int] = 60 * 2):
        self.digiseller_code = digiseller_code
        self.status = status
        self.error = None
        self.delivery_time = None
        self.time_left = None
        self.steam_profile_url = None
        self.paused = False
        self.set_delivery_time(delivery_delay)

    async def update(self, **kwargs):
        deliveries = await get()
        for key, value in kwargs.items():
            deliveries[self.digiseller_code].__setattr__(key, value)
        await storage.write(deliveries)

    async def set_status(self, status: Optional[int], message=None, error=None):
        await self.update(status=status)

    async def seterror(self, error: int):
        await self.update(error=error)

    async def pause(self):
        await self.update(paused=True, time_left=self.delivery_time - time.time())

    async def unpause(self):
        await self.update(paused=False, delivery_time=time.time() + self.time_left)

    def set_delivery_time(self, seconds=60 * 2):
        self.delivery_time = time.time() + seconds

    def get_time_until_delivery(self):
        return int(self.delivery_time - time.time())

    def todict(self):
        dictionary = self.__dict__.copy()
        return dictionary


async def get(digiseller_code: Optional[str] = None, status: Optional[int | list[int]] = None) -> \
        Optional[dict[str, Delivery] | Delivery | list[Delivery]]:
    """
    Асинхронная функция, которая возвращает информацию о доставках.

    :param digiseller_code: код продажи. Если указан, возвращает информацию о доставке для данного кода.
    :type digiseller_code: Optional[str]
    :param status: статус доставки. Если указан, возвращает список всех доставок с этим статусом. Должен быть значением из класса Status.
    :type status: Optional[DeliveryStatus]
    :return: возвращает либо словарь всех доставок, либо конкретную доставку (если указан digiseller_code), либо список доставок с указанным статусом (если указан status).
    :rtype: Optional[dict[str, Delivery] | Delivery | list[Delivery]]
    """

    # Читаем данные о доставках из хранилища
    deliveries: dict[str, Delivery] = await storage.read({})
    # Если указан код продажи, возвращаем соответствующую доставку
    if digiseller_code:
        return deliveries.get(digiseller_code, None)
    # Если указан статус, возвращаем список доставок с этим статусом
    elif status is not None:
        if type(status) is int:
            status = [status]
        return [delivery for delivery in deliveries.values() if delivery.status in status]

    # Если ничего не указано, возвращаем все доставки
    return deliveries


async def create(digiseller_code: str) -> Delivery:
    deliveries = await get()
    deliveries[digiseller_code] = Delivery(digiseller_code, DeliveryStatus.WAITING_UNTIL_DELIVERY)

    await storage.write(deliveries)

    return await get(digiseller_code)


async def set_status(digiseller_code: str, status: int):
    deliveries = await get()
    deliveries[digiseller_code].status = status


async def reset_statuses_if_not_delivered():
    deliveries = await get()
    for key in deliveries.keys():
        if deliveries[key].status != DeliveryStatus.DELIVERED:
            deliveries[key].status = DeliveryStatus.WAITING_UNTIL_DELIVERY
    await storage.write(deliveries)
