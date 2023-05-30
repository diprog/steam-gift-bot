class Message:
    """
    Класс, представляющий сообщение.

    :param id: идентификатор сообщения
    :type id: int
    :param message: текст сообщения
    :type message: str
    :param buyer: признак, что сообщение от покупателя (0 или 1), по умолчанию 0
    :type buyer: int, optional
    :param seller: признак, что сообщение от продавца (0 или 1), по умолчанию 0
    :type seller: int, optional
    :param deleted: признак, что сообщение удалено (0 или 1), по умолчанию 0
    :type deleted: int, optional
    :param date_written: дата и время отправки сообщения, по умолчанию None
    :type date_written: str, optional
    :param date_seen: дата и время прочтения сообщения, по умолчанию None
    :type date_seen: str, optional
    :param is_file: признак, что сообщение является файлом (0 или 1), по умолчанию 0
    :type is_file: int, optional
    :param filename: оригинальное название файла, по умолчанию None
    :type filename: str, optional
    :param url: URL файла, по умолчанию None
    :type url: str, optional
    :param is_img: признак, что сообщение является изображением (0 или 1), по умолчанию 0
    :type is_img: int, optional
    :param preview: URL превью изображения, по умолчанию None
    :type preview: str, optional
    """

    def __init__(self, id: int, message: str, buyer: int = 0, seller: int = 0, deleted: int = 0,
                 date_written: str = None, date_seen: str = None, is_file: int = 0, filename: str = None,
                 url: str = None, is_img: int = 0, preview: str = None):
        self.id = id
        self.message = message
        self.buyer = buyer
        self.seller = seller
        self.deleted = deleted
        self.date_written = date_written
        self.date_seen = date_seen
        self.is_file = is_file
        self.filename = filename
        self.url = url
        self.is_img = is_img
        self.preview = preview

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            message=data.get('message'),
            buyer=data.get('buyer', 0),
            seller=data.get('seller', 0),
            deleted=data.get('deleted', 0),
            date_written=data.get('date_written'),
            date_seen=data.get('date_seen'),
            is_file=data.get('is_file', 0),
            filename=data.get('filename'),
            url=data.get('url'),
            is_img=data.get('is_img', 0),
            preview=data.get('preview'),
        )