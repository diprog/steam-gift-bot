from digiseller.api import Digiseller


class ChatContainer:
    def __init__(self, chat: dict, digiseller: Digiseller):
        self.chat = chat

    async def send_message(self):