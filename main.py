import requests
import json
import logging
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, Updater, CommandHandler, ContextTypes, MessageHandler, filters

# Ваш API key от Яндекс карт (https://developer.tech.yandex.ru/services - вам нужен JavaScript API и HTTP Геокодер)
# !ВАЖНО этот же ключ нужно указать в файле webappsaymyaddress.html в <script src="https://api-maps.yandex.ru/2.1/?lang=ru_RU&amp;apikey= и в function getAddress()
YANDEX_MAPS_API_KEY = "YANDEX_MAPS_API_KEY"
# Вам нужно настроить отображение webappsaymyaddress.html на своем сервере (например website.com/webappsaymyaddress.html)
MINI_APP_HTML_URL = "YOUR_URL_TO/webappsaymyaddress.html"
# Вам нужно указать токен вашего бота (боты регистрируются через https://t.me/botfather)
MY_TELEGRAM_BOT_TOKEN = "BOT_TOKEN"

# это наша функция для получения адреса по координатам.
def get_address_from_coords(coords):

    PARAMS = {
        "apikey": YANDEX_MAPS_API_KEY,
        "format": "json",
        "lang": "ru_RU",
        "kind": "house",
        "geocode": coords
    }

    try:
        # Особенность Яндекс карт, что они воспринимают координаты в виде ДОЛГОТА, ШИРОТА
        r = requests.get(url="https://geocode-maps.yandex.ru/1.x/", params=PARAMS)
        json_data = r.json()
        address_str = json_data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["metaDataProperty"][
            "GeocoderMetaData"]["AddressDetails"]["Country"]["AddressLine"]

        # Если прошло успешно, то переворачиваем координаты в нормальный вид ШИРОТА, ДОЛГОТА
        coords = coords.replace(" ", "")
        latitude = coords.split(",")[1]
        longitude = coords.split(",")[0]
        coords_shir_dolg = latitude + ", " + longitude

        return "<code>"+address_str + "</code>\n\nКоординаты (широта, долгота):\n<code>" + coords_shir_dolg+"</code>"

    # Пробуем еще раз в случае, если что-то сорвалось при получении адреса
    except Exception as e:
        try:
            # Пробуем перевернуть координаты и дать запрос еще раз
            coords_shir_dolg = coords
            coords = coords.replace(" ", "")
            latitude = coords.split(",")[0]
            longitude = coords.split(",")[1]
            coords = longitude + ", " + latitude
            PARAMS = {
                "apikey": YANDEX_MAPS_API_KEY,
                "format": "json",
                "lang": "ru_RU",
                "kind": "house",
                "geocode": coords
            }
            r = requests.get(url="https://geocode-maps.yandex.ru/1.x/", params=PARAMS)
            json_data = r.json()
            address_str = \
            json_data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["metaDataProperty"][
                "GeocoderMetaData"]["AddressDetails"]["Country"]["AddressLine"]
            return "<code>" + address_str + "</code>\n\nКоординаты (широта, долгота):\n<code>" + coords_shir_dolg + "</code>"

        except Exception as e:
            # Если ничего не вышло, то выдаем сообщение об ошибке
            return "Не могу определить адрес по этой локации/координатам.\n\nОтправь мне локацию или координаты:"


# Эта функция будет использоваться когда человек первый нажал в боте START
async def start(update, context):
    keyboard = get_mini_app_keyboard()

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard = True)

    await update.message.reply_text(
        "Пришли <b>ЛОКАЦИЮ</b> / <b>КООРДИНАТЫ</b> или выбери на карте:",
        parse_mode = "HTML",
        reply_markup=reply_markup
    )

# Эта функция используется когда нужно получить данные координат из MiniApp
async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    # Получили данные из html страницы обратно
    data = json.loads(update.effective_message.web_app_data.data)

    keyboard = get_mini_app_keyboard()

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # вовщращаем результат пользователю в боте
    await update.message.reply_text(
        '📍 Предположительный адрес:\n<code>' + data['address'] + "</code>\n\nКоординаты (широта, долгота):\n<code>{}, {}</code>".format(data['latitude'],data['longitude']) + '\n\nYandex Maps:\nhttps://yandex.ru/maps/?pt={},{}&z=17&l=map'.format(
            data['longitude'], data['latitude']) + '\n\nGoogle Maps:\nhttp://www.google.com/maps/place/{},{}'.format(data['latitude'],data['longitude']),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=reply_markup)

# Эта функция будет использоваться, если пользователь послал в бота любой текст. Мы ожидаем координаты, но если прийдет что-то другое не страшно, ведь мы описали в функции получения адреса возвращение ошибки в случае чего.
async def text(update, context):

    keyboard = get_mini_app_keyboard()

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # получаем текст от пользователя
    coords = update.message.text
    latitide = coords.replace(' ', '').split(',')[0]
    longitude = coords.replace(' ', '').split(',')[1]
    # отправляем текст в нашу функцио получения адреса из координат
    address_str = get_address_from_coords(coords)
    # вовщращаем результат пользователю в боте
    await update.message.reply_text(
        '📍 Предположительный адрес:\n' + address_str + '\n\nYandex Maps:\nhttps://yandex.ru/maps/?pt={},{}&z=17&l=map'.format(
            longitude, latitide) + '\n\nGoogle Maps:\nhttp://www.google.com/maps/place/{},{}'.format(latitide,
                                                                                                     longitude),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=reply_markup)

def get_mini_app_keyboard():
    return [
        [
            KeyboardButton("📍 Открыть карту",
                           web_app=WebAppInfo(url=MINI_APP_HTML_URL))
        ]
    ]

# Эта функция будет использоваться, если пользователь послал локацию.
async def location(update, context):
    keyboard = [
        [
            KeyboardButton("📍 Открыть карту",
                           web_app=WebAppInfo(url="https://stepogram.shop/media/html/webappsaymyaddress.html"))
        ]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # получаем обьект сообщения (локации)
    message = update.message
    # вытаскиваем из него долготу и широту
    current_position = (message.location.longitude, message.location.latitude)
    latitide = message.location.latitude
    longitude = message.location.longitude
    # создаем строку в виде ДОЛГОТА,ШИРОТА
    coords = f"{current_position[0]}, {current_position[1]}"
    # отправляем координаты в нашу функцию получения адреса
    address_str = get_address_from_coords(coords)
    # вовщращаем результат пользователю в боте
    await update.message.reply_text(
        '📍 Предположительный адрес:\n' + address_str + '\n\nYandex Maps:\nhttps://yandex.ru/maps/?pt={},{}&z=17&l=map'.format(
            longitude, latitide) + '\n\nGoogle Maps:\nhttp://www.google.com/maps/place/{},{}'.format(latitide,longitude),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=reply_markup)


# Это основная функция, где запускается наш бот
def main():
    # создаем бота и указываем его токен
    application = Application.builder().token(MY_TELEGRAM_BOT_TOKEN).build()

    # регистрируем команду /start и говорим, что после нее надо использовать функцию def start
    application.add_handler(CommandHandler("start", start))
    # регистрируем получение текста и говорим, что после нее надо использовать функцию def text
    application.add_handler(MessageHandler(filters.TEXT, text))
    # регистрируем получение локации и говорим, что после нее надо использовать функцию def location
    application.add_handler(MessageHandler(filters.LOCATION, location))
    # регистрируем получение данных из mini app
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    # запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    # запускаем функцию def main
    main()