from __future__ import annotations

import asyncio
import logging
import os.path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Error, Browser, Playwright

from browser.utils import find_chrome_executable_path


class ChromeProcess:
    def __init__(self, remote_debugging_port: Optional[int], user_data_dir: Optional[str] = None):
        """
        Инициализирует экземпляр класса ChromeExe.

        :param remote_debugging_port: int, порт для удаленной отладки
        :param user_data_dir: str, путь к каталогу данных пользователя
        """
        self.remote_debugging_port = remote_debugging_port or 12345
        self.user_data_dir = user_data_dir
        self.pid = None

    async def start(self) -> ChromeProcess:
        """
        Асинхронно запускает Google Chrome с указанными параметрами.

        :return: ChromeExe
        """

        chrome_executable_path = find_chrome_executable_path()
        args = [
            f'--remote-debugging-port={self.remote_debugging_port}',
            '--no-sandbox',
            '--disable-sync',
        ]

        if self.user_data_dir:
            user_data_dir = os.path.abspath(self.user_data_dir)
            args.append(f'--user-data-dir="{user_data_dir}"')
        cmd = [f'"{chrome_executable_path}"'] + args
        print(' '.join(cmd))
        await asyncio.create_subprocess_shell(' '.join(cmd), stdout=asyncio.subprocess.DEVNULL,
                                              stderr=asyncio.subprocess.DEVNULL)

        return self


class Chrome:
    def __init__(self, remote_debugging_port: Optional[int], user_data_dir: Optional[str] = None):
        self.process = ChromeProcess(remote_debugging_port, user_data_dir)
        # Иницииализируются ниже
        self.playwright: Optional[Playwright]
        self.browser: Optional[Browser]
        self.context: Optional[BrowserContext]

    async def _close(self):
        page = self.browser.contexts[0].pages[0]
        client = await page.context.new_cdp_session(page)
        await client.send("Browser.close")

    async def connect_over_cdp(self) -> Browser | None:
        try:
            return await self.playwright.chromium.connect_over_cdp(
                f'http://localhost:{self.process.remote_debugging_port}')
        except Error as e:
            if 'connect ECONNREFUSED' in e.message:
                return None
            else:
                raise

    async def _attempt_connecting(self, max_attempts=5) -> Browser:
        attempts = 0
        while attempts <= max_attempts:
            if browser := await self.connect_over_cdp():
                return browser
            else:
                attempts += 1
                logging.info(f'Неудачная попытка подключения к Chrome через CDP. {attempts}')
                await asyncio.sleep(1)
        logging.error('Не удалось подключиться к Chrome через CDP.')

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        await self.process.start()
        self.browser = await self._attempt_connecting()

        if not self.browser:
            await self.__aexit__()
            raise

        self.context = self.browser.contexts[0]
        return self

    async def __aexit__(self, *_):
        await self._close()
        await self.playwright.stop()

    async def find_addtocart_button(self, page):
        # Function to evaluate in the context of the iframe
        async def find_button_in_iframe(iframe):
            button = await iframe.query_selector("div.btn_addtocart")
            return button

        # Find all iframes on the page
        iframes = page.frames

        # Iterate through iframes and search for the button
        for iframe in iframes:
            button = await find_button_in_iframe(iframe)
            if button:
                return button

        # If the button is not found in any iframe, search the main page
        return await page.query_selector("div.btn_addtocart")

    async def find_in_frames(self, page, selector):
        # Function to evaluate in the context of the iframe
        async def find_button_in_iframe(iframe):
            button = await iframe.query_selector(selector)
            return button

        # Find all iframes on the page
        iframes = page.frames

        # Iterate through iframes and search for the button
        for iframe in iframes:
            button = await find_button_in_iframe(iframe)
            if button:
                return button

        # If the button is not found in any iframe, search the main page
        return await page.query_selector(selector)
