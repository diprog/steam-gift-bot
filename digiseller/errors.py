class APIHTTPError(Exception):
    def __init__(self, json: dict):
        self.json = json
    """
    Исключение, вызываемое при возникновении ошибки при работе с API.
    """
    ...
