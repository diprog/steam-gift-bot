import re

import aiohttp
from lxml import etree

from steam import UserNotFoundError, UserProfileURLError


class XMLUserInfo:
    """
    Контейнер для функции get_user_id64_by_url.

    :param id: SteamID пользователя.
    :param id64: Уникальный 64-битный SteamID пользователя.
    :param public: Флаг публичности профиля пользователя (True - публичный, False - закрытый).
    """

    def __init__(self, id: str, id64: int, public: bool, avatar_url: str, profile_url: str):
        self.id = id
        self.id64 = id64
        self.id3 = id64_to_id3(id64)
        self.public = public
        self.avatar_url = avatar_url
        self.profile_url = profile_url


async def get_user_by_url(profile_url: str) -> XMLUserInfo:
    """
    Получает информацию о пользователе по URL профиля в формате XML.

    :param profile_url: URL профиля пользователя Steam.
    :return: Объект класса XMLUserInfo с информацией о пользователе.
    :raises UserNotFoundError: Если указанный профиль не найден.
    :raises UserProfileURLError: Если возникла ошибка с URL профиля.
    """

    # Создание асинхронной сессии
    async with aiohttp.ClientSession() as session:
        # Запрос к странице профиля с параметром ?xml=1 для получения данных в формате XML
        xml_profile_url = profile_url + '?xml=1' if profile_url[-1] == '/' else profile_url + '/?xml=1'
        async with session.get(xml_profile_url) as r:
            print(r.url)
            # Если статус ответа 200 (успешно)
            if r.status == 200:
                # Создание дерева XML из ответа
                xml_tree = etree.fromstring(await r.read())

                # Проверка на наличие ошибки в ответе
                if error := xml_tree.xpath('//error'):
                    # Если профиль не найден
                    if error[0].text == 'The specified profile could not be found.':
                        raise UserNotFoundError
                    else:
                        # Если возникла другая ошибка с URL профиля
                        raise UserProfileURLError(error[0].text)

                # Возвращает объект класса XMLUserInfo с информацией о пользователе
                return XMLUserInfo(
                    xml_tree.find('steamID').text,
                    int(xml_tree.find('steamID64').text),
                    xml_tree.find('privacyState').text == 'public',
                    xml_tree.find('avatarFull').text,
                    profile_url)


def find_steam_profile_url_in_text(text):
    steam_url_pattern = re.compile(r'https?://steamcommunity.com/(id|profiles)/[a-zA-Z0-9-_]+')
    match = steam_url_pattern.search(text)
    if match:
        return match.group()
    else:
        return None


def id64_to_id3(id64: int):
    return id64 - 76561197960265728
