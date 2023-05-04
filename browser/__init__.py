import asyncio
import logging
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Error, Browser, Playwright


class Chrome:
    def __init__(self, remote_debugging_host: str):
        self.remote_debugging_host = remote_debugging_host
        # Иницииализируются ниже
        self.playwright: Optional[Playwright]
        self.browser: Optional[Browser]
        self.context: Optional[BrowserContext]

    async def _close(self):
        page = self.browser.contexts[0].pages[0]
        client = await page.context.new_cdp_session(page)
        await client.send("Browser.close")

    async def _attempt_connecting(self, max_attempts=3) -> Browser:
        attempts = 0
        while attempts <= max_attempts:
            try:
                return await self.playwright.chromium.connect_over_cdp(self.remote_debugging_host)
            except Error as e:
                if 'connect ECONNREFUSED' in e.message:
                    attempts += 1
                    await asyncio.sleep(1)
                else:
                    raise
        logging.error('Не удалось подключиться к браузеру')

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self._attempt_connecting()

        if not self.browser:
            await self.playwright.stop()

        self.context = self.browser.contexts[0]
        return self

    async def __aexit__(self, *_):
        await self._close()
        await self.playwright.stop()
