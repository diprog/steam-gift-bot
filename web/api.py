import time

from aiohttp import web, InvalidURL
from jsonpickle import Pickler

import db
from db.models.deliveries import DeliveryStatus
from digiseller.api import Digiseller
from digiseller.errors import APIHTTPError
from steam import get_user_by_url, Steam
from utils import format_duration

api_routes = web.RouteTableDef()

pickler = Pickler(unpicklable=True)


@api_routes.post('/api/get_steam_profile_info')
async def get_steam_profile_info(request: web.Request):
    data = await request.post()
    user = await get_user_by_url(data['steam_profile_url'])
    return web.json_response(user.__dict__)


@api_routes.post('/api/deliveries/get')
async def get_purchase_info(request: web.Request):
    data = await request.post()
    digiseller_code = data['code']
    print(digiseller_code)
    digiseller: Digiseller = request.app['digiseller']
    try:
        purchase = await digiseller.get_purchase_by_code(digiseller_code)
        print(purchase)
        if purchase.get('errors'):
            print(purchase['errors'])
    except APIHTTPError as e:
        print(e.json)
        return
    delivery = await db.deliveries.get(digiseller_code) or await db.deliveries.create(digiseller_code)
    if not delivery.steam_profile_url:
        await delivery.update(steam_profile_url=purchase['options'][0]['value'])
        # await delivery.update(steam_profile_url='https://steamcommunity.com/profiles/76561198192279965/')
    return web.json_response({'delivery': pickler.flatten(delivery), 'purchase': purchase})


@api_routes.post('/api/deliveries/get_time_until_delivery')
async def get_time_until_delivery(request: web.Request):
    data = await request.post()
    digiseller_code = data['code']
    delivery = await db.deliveries.get(digiseller_code)
    time_until_delivery = delivery.get_time_until_delivery()
    time_until_delivery_string = '' if time_until_delivery <= 0 else format_duration(time_until_delivery)
    return web.json_response({'time': time_until_delivery_string})


@api_routes.post('/api/deliveries/force_start')
async def get_time_until_delivery(request: web.Request):
    data = await request.post()
    digiseller_code = data['code']
    delivery = await db.deliveries.get(digiseller_code)
    await delivery.update(delivery_time=time.time(), paused=False)
    return web.json_response({'ok': True})


@api_routes.post('/api/deliveries/pause')
async def get_time_until_delivery(request: web.Request):
    data = await request.post()
    digiseller_code = data['code']
    delivery = await db.deliveries.get(digiseller_code)
    await delivery.pause()
    return web.json_response({'ok': True})


@api_routes.post('/api/deliveries/unpause')
async def get_time_until_delivery(request: web.Request):
    data = await request.post()
    digiseller_code = data['code']
    delivery = await db.deliveries.get(digiseller_code)
    await delivery.unpause()
    return web.json_response({'ok': True})


@api_routes.post('/api/deliveries/set_steam_profile_url')
async def set_steam_profile_url(request: web.Request):
    data = await request.post()
    digiseller_code = data['code']
    steam_profile_url = data['steam_profile_url'].strip()
    if not steam_profile_url.replace(' ', ''):
        return web.json_response({'error': 'Вы ничего не ввели в поле.'})
    delivery = await db.deliveries.get(digiseller_code)
    if delivery.get_time_until_delivery() < 0 or delivery.status != DeliveryStatus.WAITING_UNTIL_DELIVERY:
        return web.json_response({'error': 'Доставка уже началась.\nПоменять ссылку нельзя.'})
    try:
        user = await get_user_by_url(steam_profile_url)
        if not user.public:
            return web.json_response({'error': 'Указанный профиль закрыт (не публичный). Откройте его.'})

        await delivery.update(steam_profile_url=steam_profile_url)
        return web.json_response({'error': ''})
    except InvalidURL:
        return web.json_response({'error': 'Вы ввели неправильную ссылку.\nУбедитесь, что она начинается с https://'})


@api_routes.post('/api/deliveries/check_for_new_status')
async def check_for_new_status(request: web.Request):
    data = await request.post()
    digiseller_code = data['code']
    delivery_status = int(data['delivery_status'])
    delivery = await db.deliveries.get(digiseller_code)
    if delivery.error:
        return web.json_response({'new_status': -1, 'error': delivery.error})
    if delivery_status != delivery.status:
        return web.json_response({'new_status': delivery.status})
    else:
        return web.json_response({'new_status': -1})


@api_routes.post('/api/get_courier_steam_profile')
async def get_courier_steam_profile(request: web.Request):
    steam: Steam = request.app['steam']
    profile = await get_user_by_url(await steam.get_my_profile_url())
    return web.json_response({'profile': profile.__dict__})
