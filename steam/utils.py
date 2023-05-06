from lxml import etree
import aiohttp

class XMLUserInfo:
    """
    Контейнер для функции get_user_id64_by_url
    """
    def __init__(self, id64: str, public: bool):
        self.id64 = id64
        self.public = public


async def get_user_by_url(profile_url: str) -> XMLUserInfo:
    async with aiohttp.ClientSession() as session:
        async with session.get(profile_url + '?xml=1') as r:
            xml_tree = etree.fromstring(await r.read())
            id64 = xml_tree.find('steamID64').text
            public = xml_tree.find('privacyState').text == 'public'
            return XMLUserInfo(id64, public)
