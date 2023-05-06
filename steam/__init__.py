import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator, Optional

from playwright.async_api import Page, TimeoutError

from browser import Chrome
from steam.errors import *
from steam.utils import get_user_by_url
from utils import convert_russian_datetime


class AuthContext:
    def __init__(self, auth_page: Page, steam_guard_required: bool = False):
        self.auth_page = auth_page
        self.steam_guard_required = steam_guard_required
        self.code_requested_ts: Optional[float] = None

    async def enter_auth_steam_guard_code(self, code: str):
        """
        Вводит код Steam Guard в поле на странице авторизации.

        :param code: код Steam Guard для ввода на странице.
        :type code: str
        :raises SteamGuardCodeFormatError: В случае, если формат кода Steam Guard некорректен.
        :raises SteamGuardCodeError: В случае, если код Steam Guard неверен.
        :returns: None. Функция предназначена для завершения процесса авторизации на Steam.
        """
        char_inputs = await self.auth_page.query_selector_all(
            '//div[@class="newlogindialog_SegmentedCharacterInput_1kJ6q"]//input')
        async with self.auth_page.expect_response('**UpdateAuthSessionWithSteamGuardCode/v1') as response_info:
            for i, char_input in enumerate(char_inputs):
                try:
                    await char_input.fill(code[i])
                except IndexError:
                    raise SteamGuardCodeFormatError()

        response = await response_info.value
        for header in await response.headers_array():
            if header['name'] == 'x-eresult':
                if header['value'] != '1':
                    raise SteamGuardCodeError()

        # Просто ждем, пока выполнится последний запрос в цепочке авторизации.
        async with self.auth_page.expect_response('https://steam.tv/login/settoken'):
            ...

        logging.info('Авторизация Steam прошла успешно.')


class Steam(Chrome):
    def __init__(self, remote_debugging_host: str):
        """
        Инициализация объекта Steam. Используется удаленный хост для отладки.
        :param remote_debugging_host: адрес удаленного хоста для отладки
        """
        super().__init__(remote_debugging_host)

    @asynccontextmanager
    async def auth_start(self, login: str, password: str) -> AsyncIterator[AuthContext]:
        """
        Это менеджер контекста, поэтому используйте `async with start_auth() as auth`.
        Для завершения авторизации используйте метод auth_steam_guard_code внутри этого контекста.
        :param login: логин от аккаунта Steam
        :param password: пароль от аккаунта Steam
        :return:
        """
        page = await self.context.new_page()
        await page.goto('https://steamcommunity.com/login/home/', wait_until='networkidle')
        auth_context = AuthContext(page)
        try:
            # Проверяем, есть ли активная авторизация.
            if 'login/home' not in page.url:
                steam_login = await page.text_content('//span[@class="persona online"]')
                raise AlreadyAuthorizedError(steam_login)

            # Вводим логин и пароль.
            form_inputs_selector = '//input[@class="newlogindialog_TextInput_2eKVn"]'
            await page.wait_for_selector(form_inputs_selector)
            elements = await page.query_selector_all(form_inputs_selector)
            await elements[0].fill(login)
            await elements[1].fill(password)

            # Нажимаем на чекбокс "Запомнить меня", если он не активен.
            remember_me_checkbox = await page.query_selector('//div[@class="newlogindialog_Checkbox_3tTFg"]')
            is_enabled = (await remember_me_checkbox.inner_html()) != ''
            if not is_enabled:
                await remember_me_checkbox.click()

            # нажимаем на кнопку "Войти".
            auth_context.code_requested_ts = time.time()
            await page.click('//button[@class="newlogindialog_SubmitButton_2QgFE"]')
            await page.wait_for_load_state('networkidle')

            # Если аккаунт сразу авторизовало, не потребовав ввести код Steam Guard.
            if 'login' not in page.url:
                if username := await self.get_self():
                    logging.info(f'Авторизация Steam ({username}) прошла успешно. Код Steam Guard не требуется.')
                    auth_context.steam_guard_required = False
            else:
                # Ждем появления поля для ввода кода Steam Guard.
                await page.wait_for_selector('//div[@class="newlogindialog_SegmentedCharacterInput_1kJ6q"]',
                                             timeout=10000)
                auth_context.steam_guard_required = True
            yield AuthContext(page, steam_guard_required=True)
        except TimeoutError:
            logging.info('TimeoutError - не появилась поле ввода кода Steam Guard')
        finally:
            await page.close()

    async def get_steam_guard_code_from_mailru(self, login: str, password: str, code_requested_ts: float):
        """
        Получает код Steam Guard из аккаунта электронной почты mail.ru.

        :param login: Логин аккаунта электронной почты mail.ru.
        :type login: str
        :param password: Пароль аккаунта электронной почты mail.ru.
        :type password: str
        :raises MailRuLoginError: В случае неудачной авторизации.
        :returns: None. Эта функция предназначена для прохождения процесса авторизации и получения кода Steam Guard.
        """
        page = await self.context.new_page()
        await page.goto('https://light.mail.ru/search/?search=&q_query=steam+guard&st=search', wait_until='networkidle')

        if 'login' in page.url:
            # Заполнение поля ввода имени пользователя, предоставленным логином.
            await page.fill('//input[@name="username"]', login)
            await page.click('//button[@type="submit"]')

            # Заполнение поля ввода пароля предоставленным паролем.
            await page.fill('//input[@name="password"]', password)
            async with page.expect_response('https://auth.mail.ru/cgi-bin/auth') as response_info:
                await page.click('//button[@type="submit"]')
            response = await response_info.value
            for header in await response.headers_array():
                if header['name'] == 'Location' and 'fail' in header['value']:
                    raise MailRuLoginError

            logging.info('Авторизация mail.ru прошла успешно.')

            await page.wait_for_load_state('networkidle', timeout=2000)

            await page.wait_for_selector('//td[@class="messageline__date messageline__item"]')
            while True:
                mail_rows = await page.query_selector_all('//tr[@class="messageline messageline_unread"]')
                for mail_row in mail_rows:
                    datetime_string = await (
                        await mail_row.query_selector(
                            '//td[@class="messageline__date messageline__item"]')).get_attribute(
                        'title')
                    print(datetime.now())
                    print(convert_russian_datetime(datetime_string))
                await asyncio.sleep(10)

    async def get_self(self) -> str | None:
        """
        Проверяет, авторизован ли текущий аккаунт Steam.

        Возвращает логин для входа на сайт Steam, если аккаунт авторизован.
        Если аккаунт не авторизован, возвращает None.

        :return: логин для входа (str) или None, если аккаунт не авторизован
        :rtype: str | None
        """
        page = await self.context.new_page()
        await page.goto('https://steamcommunity.com/')

        # Проверяем авторизацию по цвету кнопки "Установить Steam" в верхней части сайта.
        gray_or_green_button_div = await page.wait_for_selector(
            '//div[@class="header_installsteam_btn header_installsteam_btn_gray"]|'
            '//div[@class="header_installsteam_btn header_installsteam_btn_green"]')
        div_class = await gray_or_green_button_div.get_attribute('class')

        # Если кнопка зеленая, значит аккаунт не авторизован.
        try:
            if div_class.endswith('green'):
                return None
            else:
                return await page.text_content('//span[@class="persona online"]')
        finally:
            await page.close()

    async def buy_game(self, game_url: str):
        page = await self.context.new_page()
        await page.goto(game_url, wait_until='networkidle')
        await page.click('//a[@id="btn_add_to_cart_65766"]')
        await page.wait_for_url('**/cart/', wait_until='networkidle')
        await page.click('//a[@id="btn_purchase_self"]')
        logging.info('Ждем')
        await asyncio.sleep(10000)

    async def send_friend_invite(self, user_url: str):
        user = await get_user_by_url(user_url)

        if not user.public:
            raise UserProfileNotPublicError

        page = await self.context.new_page()
        await page.goto(user_url, wait_until='networkidle')
        async with page.expect_response('**/AddFriendAjax') as response_info:
            await page.click('//a[@id="btn_add_friend"]')
        response = await response_info.value
        json = await response.json()
        if response.status == 400:
            if json.get('failed_invites'):
                if user.id64 in json['failed_invites']:
                    raise UserFriendInviteFailed(await page.text_content('//div[@class="newmodal_content"]'))