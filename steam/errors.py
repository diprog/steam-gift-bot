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


class UserProfileNotPublicError(Exception):
    ...


class UserFriendInviteFailed(Exception):
    ...


class UserNotFoundError(Exception):
    ...


class UserProfileURLError(Exception):
    ...


class IsFriendAlreadyError(Exception):
    def __init__(self, friend_id3: int):
        self.friend_id3 = friend_id3


class AlreadyOwnsGameError(Exception):
    ...

class AlreadySentFriendRequestError(Exception):
    ...