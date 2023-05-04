from datetime import datetime

import pytz


def convert_russian_datetime(russian_datetime_str: str) -> datetime:
    """
    Конвертирует строку с датой и временем на русском языке в объект datetime с поддержкой часовых поясов.

    :param russian_datetime_str: Строка с датой и временем на русском языке.
    :type russian_datetime_str: str
    :return: Объект datetime с поддержкой часовых поясов.
    :rtype: datetime
    """
    # Определение формата строки с датой и временем на русском языке.
    format_str = "%A, %d %B %Y, %H:%M %z"

    # Создание словаря для преобразования русских названий месяцев в английские.
    month_translation = {
        "января": "January",
        "февраля": "February",
        "марта": "March",
        "апреля": "April",
        "мая": "May",
        "июня": "June",
        "июля": "July",
        "августа": "August",
        "сентября": "September",
        "октября": "October",
        "ноября": "November",
        "декабря": "December"
    }

    # Замена русских названий месяцев на английские.
    for rus_month, eng_month in month_translation.items():
        russian_datetime_str = russian_datetime_str.replace(rus_month, eng_month)

    # Создание словаря для преобразования русских названий дней недели в английские.
    weekday_translation = {
        "Понедельник": "Monday",
        "Вторник": "Tuesday",
        "Среда": "Wednesday",
        "Четверг": "Thursday",
        "Пятница": "Friday",
        "Суббота": "Saturday",
        "Воскресенье": "Sunday"
    }

    # Замена русских названий дней недели на английские.
    for rus_weekday, eng_weekday in weekday_translation.items():
        russian_datetime_str = russian_datetime_str.replace(rus_weekday, eng_weekday)

    # Преобразование строки с датой и временем в объект datetime с поддержкой часовых поясов.
    dt = datetime.strptime(russian_datetime_str, format_str)
    dt = dt.replace(tzinfo=pytz.UTC)

    return dt
