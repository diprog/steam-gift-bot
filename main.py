import asyncio
import logging
import ssl
import traceback
from pathlib import Path

from aiohttp import web

import constants
import db
from db.models.deliveries import DeliveryStatus
from digiseller.api import Digiseller
from display import start_display, stop_display
from steam import get_user_by_url, UserNotFoundError, Steam, IsFriendAlreadyError, \
    UserProfileNotPublicError, AlreadyOwnsGameError, UserFriendInviteFailed, AlreadySentFriendRequestError, AuthContext, \
    AlreadyAuthorizedError
from steam.utils import find_steam_profile_url_in_text
from utils import find_steam_product_url
from web.api import api_routes

routes = web.RouteTableDef()

gift_semaphore = asyncio.Semaphore(1)


@routes.get('/delivery')
async def delivery_page(request: web.Request):
    return web.Response(text=open('html/delivery.html', 'r', encoding='utf-8').read(), content_type='text/html')


@routes.get('/delivery_redirect')
async def delivery_page(request: web.Request):
    print('got')
    print(request.url.query['uniquecode'], request.url)


@routes.post('/check_steam_profile_url')
async def check_steam(request: web.Request):
    data = await request.json()

    if steam_profile_url := find_steam_profile_url_in_text(data['options'][0]['value']):
        try:
            user = await get_user_by_url(steam_profile_url)
            if not user.public:
                return web.json_response(
                    {'error': 'Ваш профиль закрыт. Сделайте пофиль открытым/публичным и попробуйте ещё раз. Спасибо.'})
            else:
                print('ok')
                return web.json_response({'error': ''})
        except UserNotFoundError:
            return web.json_response(
                {'error': 'Не найден профиль Steam по указанной ссылке. Убедитесь, что правильно ввели URL.'})
    else:
        return web.json_response(
            {'error': 'Не найден профиль Steam по указанной ссылке. Убедитесь, что правильно ввели URL.'})


async def handle_delivery(digiseller: Digiseller, steam: Steam, delivery: db.deliveries.Delivery):
    await delivery.set_status(DeliveryStatus.GETTING_PURCHASE_INFO)
    purchase = await digiseller.get_purchase_by_code(delivery.digiseller_code)
    product = await digiseller.get_product(purchase['id_goods'])
    steam_product_url = find_steam_product_url(product['info'], 'Подробнее о товаре: ')
    user_steam_profile = await get_user_by_url(delivery.steam_profile_url)
    if not steam_product_url:
        await delivery.seterror(5)
        return
    try:
        await delivery.set_status(DeliveryStatus.SENDING_FRIEND_INVITE)
        try:
            await steam.send_friend_invite(delivery.steam_profile_url)
        except IsFriendAlreadyError:
            await steam.remove_frined(delivery.steam_profile_url)
            await steam.send_friend_invite(delivery.steam_profile_url)
        except AlreadySentFriendRequestError:
            pass
        await delivery.set_status(DeliveryStatus.AWAITING_FRIEND_INVITATION_ACCEPT)
        print(user_steam_profile.id64)
        if await steam.wait_for_friend_request_accept(user_steam_profile.id64):
            await delivery.set_status(DeliveryStatus.SENDING_GIFT)

            async def gift_coro():
                async with gift_semaphore:
                    try:
                        await steam.gift_game(
                            steam_product_url,
                            user_steam_profile.id3, 513)
                        await delivery.set_status(DeliveryStatus.DELIVERED)
                    except AlreadyOwnsGameError:
                        await delivery.seterror(0)
                    except:
                        await delivery.seterror(1)
                        logging.error(traceback.format_exc())
                    finally:
                        await steam.remove_frined(delivery.steam_profile_url)

            asyncio.create_task(gift_coro())
        # Если вышло время ожидания принятия заявки в друзья.
        else:
            await delivery.seterror(2)
    except UserProfileNotPublicError:
        await delivery.seterror(3)
    except UserFriendInviteFailed:
        await delivery.seterror(4)


async def polling(steam: Steam, digiseller: Digiseller):
    print('Поллинг')
    while True:
        deliveries = await db.deliveries.get(status=[
            DeliveryStatus.WAITING_UNTIL_DELIVERY
        ])
        print(deliveries)
        for delivery in deliveries:
            print(delivery.get_time_until_delivery())
            if delivery.get_time_until_delivery() <= 0 and not delivery.paused:
                asyncio.create_task(
                    handle_delivery(digiseller, steam, delivery))
        await asyncio.sleep(1)


async def on_startup(app):
    start_display()
    steam = await Steam(user_data_dir='.chrome', login='aoki_kz1', password='a0dEsTNYk_').__aenter__()
    try:
        auth: AuthContext
        async with steam.auth_start() as auth:
            if auth.steam_guard_required:
                ...
                # code = await steam.get_steam_guard_code_from_mailru('aoki5179@aokiplus.store', '7-Ii0HRtbh',
                #                                                     auth.code_requested_ts)
                # await auth.enter_auth_steam_guard_code(code)
    except AlreadyAuthorizedError as e:
        logging.info(f'Steam - Авторизован как {e.login}')
    except RuntimeError:
        pass

    await steam.clear_cart()

    steam.start_friend_list_updater()
    app['steam'] = steam

    digiseller = Digiseller(constants.SELLER_ID, constants.DIGISELLER_API_KEY)
    app['digiseller'] = digiseller

    asyncio.create_task(polling(steam, digiseller))


async def on_cleanup(app):
    await app['steam'].__aexit__()
    stop_display()


def main():
    app = web.Application()
    app.add_routes(api_routes)
    app.add_routes(routes)
    app.add_routes([
        web.static('/js', Path(__file__).parent.resolve() / 'html/js'),
        web.static('/css', Path(__file__).parent.resolve() / 'html/css'),
        web.static('/bootstrap/js', Path(__file__).parent.resolve() / 'html/bootstrap/js'),
        web.static('/bootstrap/css', Path(__file__).parent.resolve() / 'html/bootstrap/css')
    ])
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain('/etc/letsencrypt/live/aokistore.ru/fullchain.pem',
                                '/etc/letsencrypt/live/aokistore.ru/privkey.pem')
    web.run_app(app, host='0.0.0.0', port=443, ssl_context=ssl_context)


if __name__ == '__main__':
    main()
