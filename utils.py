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


def get_current_moscow_date_string():
    # Создаем объект часового пояса для Москвы
    moscow_tz = pytz.timezone('Europe/Moscow')

    # Получаем текущую дату и время в этом часовом поясе
    current_datetime = datetime.now(moscow_tz)
    return current_datetime.strftime('%Y-%m-%d %H:%M:%S')


def find_steam_product_url(text: str, splitter: str):
    print(text)
    for part in text.split(splitter):
        if '/' in part:
            return part.split()[0]


def format_duration(seconds):
    parts = []

    hours = seconds // 3600
    if hours > 0:
        parts.append(russian_plural(hours, ['час', 'часа', 'часов']))

    minutes = (seconds % 3600) // 60
    if minutes > 0:
        parts.append(russian_plural(minutes, ['минуту', 'минуты', 'минут']))

    seconds = seconds % 60
    parts.append(russian_plural(seconds, ['секунду', 'секунды', 'секунд']))

    return ' '.join(parts)

def russian_plural(n, forms):
    if n % 10 == 1 and n % 100 != 11:
        form = 0
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        form = 1
    else:
        form = 2
    return f"{n} {forms[form]}"
