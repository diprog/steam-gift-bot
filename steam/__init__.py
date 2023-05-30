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
    def __init__(self, remote_debugging_port: Optional[int] = None, user_data_dir: Optional[str] = None,
                 login: Optional[str] = None, password: Optional[str] = None):
        super().__init__(remote_debugging_port, user_data_dir)
        self.login = login
        self.password = password
        self.friends = []

    async def fill_auth_form_and_submit(self, page: Page):
        # Вводим логин и пароль.
        form_inputs_selector = '//input[@class="newlogindialog_TextInput_2eKVn"]'
        await page.wait_for_selector(form_inputs_selector)
        elements = await page.query_selector_all(form_inputs_selector)
        await elements[0].fill(self.login)
        await elements[1].fill(self.password)

        # Нажимаем на чекбокс "Запомнить меня", если он не активен.
        remember_me_checkbox = await page.query_selector('//div[@class="newlogindialog_Checkbox_3tTFg"]')
        is_enabled = (await remember_me_checkbox.inner_html()) != ''
        if not is_enabled:
            await remember_me_checkbox.click()

        # нажимаем на кнопку "Войти".
        await page.click('//button[@class="newlogindialog_SubmitButton_2QgFE"]')

    @asynccontextmanager
    async def auth_start(self) -> AsyncIterator[AuthContext]:
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

            auth_context.code_requested_ts = time.time()
            await self.fill_auth_form_and_submit(page)
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

    async def get_my_id64(self):
        cookies = await self.context.cookies('https://steamcommunity.com')
        for cookie in cookies:
            if cookie['name'] == 'steamLoginSecure':
                return cookie['value'].split('%', 1)[0]

    async def get_my_profile_url(self):
        my_id64 = await self.get_my_id64()
        return f'https://steamcommunity.com/profiles/{my_id64}'

    async def get_my_friends(self):
        """
        :return: Список, состоящий из ID64 друзей.
        """
        my_profile_url = await self.get_my_profile_url()
        page = await self.context.new_page()
        try:
            await page.goto(my_profile_url + '/friends')
            elements = await page.query_selector_all('//div[@id="search_results"]//div[@data-steamid]')
            self.friends = [int((await e.get_attribute('data-steamid'))) for e in elements]
        finally:
            await page.close()

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

    async def clear_cart(self):
        page = await self.context.new_page()
        try:
            await page.goto('https://store.steampowered.com/cart/')

            # Проверяем, есть ли вообще что-то в корзине.
            cart_button = await page.wait_for_selector('//div[@id="store_header_cart_btn"]', state='attached')

            # Корзина уже пустая
            if await cart_button.get_attribute('style'):
                return

            # Очищаем корзину. Нажимаем на "Удалить все товары" и подтверждаем действие.
            await page.click('//div[@class="remove_ctn"]')
            await page.click('//div[@class="btn_green_steamui btn_medium"]')
            await page.wait_for_load_state('load')
        finally:
            await page.close()

    async def gift_game(self, game_url: str, user_steam_id3: int, credit_card_cvv: int):
        """
        Асинхронная функция для покупки игры на Steam по URL игры и последующего подарка пользователю.

        :param game_url: Строка, представляющая URL страницы игры в магазине Steam.
        :param user_steam_id3: Целочисленное значение, представляющее steamID3 пользователя, которому следует подарить игру.
        :param credit_card_cvv: Целочисленное значение, представляющее CVV кредитной карты.
        """

        # Создаем новую вкладку
        page = await self.context.new_page()
        try:
            # Переходим на страницу игры
            await page.goto(game_url, wait_until='load')
            # Нажимаем кнопку "Добавить в корзину"
            add_to_cart_btn = await self.find_addtocart_button(page)
            try:
                async with self.context.expect_page(timeout=2000) as new_page_info:
                    await add_to_cart_btn.click()  # Opens a new tab
                page = await new_page_info.value
            except TimeoutError:
                pass

            # Нажимаем кнопку "Купить в подарок"
            await page.click('#btn_purchase_gift')
            await page.wait_for_load_state('networkidle')

            # Если требуется повторная авторизация, заполняем форму.
            if 'login' in page.url:
                await self.fill_auth_form_and_submit(page)

            # Выбираем пользователя, которому хотим подарить игру.
            xpath = f'//img[@data-miniprofile="{user_steam_id3}"]'
            friend_select_option = await page.wait_for_selector(xpath)
            if await page.query_selector(xpath + '/../..//div[@class="friend_ownership_info already_owns"]'):
                raise AlreadyOwnsGameError
            await friend_select_option.click()

            # Нажимаем кнопку "Продолжить"
            await page.click('//a[@class="btnv6_green_white_innerfade btn_medium"]')

            # Заполняем поля формы
            await page.fill('//input[@id="gift_recipient_name"]', 'Клиенту')  # Имя получателя
            await page.fill('//textarea[@id="gift_message_text"]',
                            'Приятной игры! Не забудьте оставить отзыв о нашем сервисе. Благодарим Вас за покупку. С уважением, Aoki Store.')  # Записка к подарку (не более 160 символов)
            await page.fill('//input[@id="gift_signature"]', 'Aoki Store')  # Подпись отправителя
            await page.click('//a[@id="submit_gift_note_btn"]')

            try:
                # Вводим CVV кредитной карты
                await page.fill('#security_code_cached', str(credit_card_cvv), timeout=5000)
            except TimeoutError:
                pass
            # Принимаем условия лицензионного соглашения
            await page.click('#accept_ssa')
            # Совершаем покупку игры
            await page.click('#purchase_button_bottom')
        finally:
            await page.close()

    async def send_friend_invite(self, user_url: str) -> int | None:
        """
        Асинхронная функция для отправки приглашения в друзья на Steam по URL профиля пользователя.

        :param user_url: Строка, представляющая URL профиля пользователя Steam.
        :return: Возвращает целочисленное значение последней части steamID3 в случае успешной отправки приглашения, иначе None.
        :raises UserProfileNotPublicError: Выбрасывает исключение, если профиль пользователя закрыт.
        :raises UserFriendInviteFailed: Выбрасывает исключение, если отправка приглашения в друзья не удалась.
        """

        # Извлекаем информацию о пользователе по предоставленному URL
        user = await get_user_by_url(user_url)

        # Проверяем, открыт ли профиль пользователя
        if not user.public:
            raise UserProfileNotPublicError

        # Открываем новую страницу и переходим по URL профиля пользователя
        page = await self.context.new_page()
        try:
            await page.goto(user_url, wait_until='networkidle')

            steam_id3 = int(
                await page.get_attribute(
                    '//div[@class="playerAvatar profile_header_size online"]|//div[@class="playerAvatar profile_header_size offline"]',
                    'data-miniprofile'))
            # Находим кнопку "Добавить в друзья"
            invite_friend_btn = await page.query_selector('//a[@id="btn_add_friend"]')

            if not invite_friend_btn:
                raise IsFriendAlreadyError(steam_id3)
            elif 'CancelInvite' in await invite_friend_btn.get_attribute('href'):
                raise AlreadySentFriendRequestError
            # Инициируем ожидание ответа сервера после нажатия на кнопку "Добавить в друзья"
            async with page.expect_response('**/AddFriendAjax') as response_info:
                await invite_friend_btn.click()
            response = await response_info.value
            json = await response.json()

            # Обработка ответа от сервера
            if response.status == 200:
                logging.info(f'Steam - Запрос в друзья успешно отправлен пользователю "{user.id}" ({user.id64})')
                return steam_id3
            elif response.status == 400:
                # Если отправка приглашения не удалась, проверяем, существует ли в ответе информация о неудачных приглашениях
                if json.get('failed_invites'):
                    if user.id64 in json['failed_invites']:
                        raise UserFriendInviteFailed(await page.text_content('//div[@class="newmodal_content"]'),
                                                     user_url)
            else:
                # Логируем неожиданный статус ответа
                logging.error(response.status)
        finally:
            await page.close()

    async def wait_for_friend_request_accept(self, user_steam_id64, timeout=60 * 10):
        timeout_time = time.time() + timeout
        while time.time() < timeout_time:
            print(user_steam_id64, self.friends)
            if int(user_steam_id64) in self.friends:
                return True
            await asyncio.sleep(1)
        return False

    def start_friend_list_updater(self):
        async def updater():
            while True:
                await self.get_my_friends()
                await asyncio.sleep(10)

        asyncio.create_task(updater())

    async def remove_frined(self, profile_url: str):
        page = await self.context.new_page()
        try:
            await page.goto(profile_url)
            await page.click('//span[@id="profile_action_dropdown_link"]')
            await asyncio.sleep(1)
            await page.click('//a[@href="javascript:RemoveFriend();"]')
            async with page.expect_response('**RemoveFriendAjax') as response_info:
                await page.click('//div[@class="btn_green_steamui btn_medium"]')
            response = await response_info.value
            await self.get_my_friends()
        finally:
            await page.close()
