import logging
import sys

from pyvirtualdisplay import Display

display = None


def start_display():
    global display
    if not display and sys.platform == "linux":
        logging.info('Дисплей - Запуск...')
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        logging.info('Дисплей - Запущен.')


def stop_display():
    global display
    if display:
        logging.info('Дисплей - Остановка...')
        display.stop()
        logging.info('Дисплей - Остановлен.')
