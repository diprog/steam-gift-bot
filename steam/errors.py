class AlreadyAuthorizedError(Exception):
    def __init__(self, login: str):
        self.login = login


class SteamGuardCodeError(Exception):
    """
    Код не прошел проверку стимом.
    """
    ...


class SteamGuardCodeFormatError(Exception):
    """
    Неверный формат кода SteamGuard (неверная длина).
    """
    ...

class MailRuLoginError(Exception):
    ...