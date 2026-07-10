class DailyEnglishError(Exception):
    """Base class for expected application errors."""


class InvalidInviteCodeError(DailyEnglishError):
    pass


class InviteCodeExpiredError(DailyEnglishError):
    pass


class InviteCodeRedeemedError(DailyEnglishError):
    pass


class InviteCodeRevokedError(DailyEnglishError):
    pass


class AlreadyRegisteredError(DailyEnglishError):
    pass


class UserBlockedError(DailyEnglishError):
    pass
