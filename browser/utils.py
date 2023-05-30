import os
import sys


def find_chrome_executable_path():
    """
    Определяет путь к исполняемому файлу Google Chrome.

    Returns:
        str: Путь к исполняемому файлу Google Chrome или None, если файл не найден.
    """

    # Определение операционной системы
    platform = sys.platform

    # Формирование списка возможных путей к исполняемому файлу Google Chrome
    if platform == "win32":
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        chrome_paths = [
            os.path.join(program_files, "Google\\Chrome\\Application\\chrome.exe"),
            os.path.join(program_files_x86, "Google\\Chrome\\Application\\chrome.exe"),
        ]
    elif platform == "linux":
        chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
    elif platform == "darwin":
        chrome_paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    else:
        raise ValueError("Unsupported platform: {}".format(platform))

    # Поиск исполняемого файла Google Chrome
    for chrome_path in chrome_paths:
        if os.path.isfile(chrome_path):
            return chrome_path

    return None
