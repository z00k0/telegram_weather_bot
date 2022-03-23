import tzlocal
import requests
import json
import datetime as dt
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.markdown import hbold
import os
import sys
import logging

API_TOKEN = os.getenv('WEATHER_BOT_TOKEN')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

DAYS_OF_WEEK = ('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    filename='openweather_bot.log',
    format='%(asctime)s %(levelname)s:%(message)s',
    encoding="UTF-8",
)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)


def get_cities_json(_city):
    geo_url = f'https://api.openweathermap.org/geo/1.0/direct?q={_city}&limit=5&appid={OPENWEATHER_API_KEY}'
    cities_response = requests.get(geo_url)

    if cities_response.status_code == 200:
        cities_json = json.loads(cities_response.text)
    else:
        sys.exit(f'Ошибка: Status Code {cities_response.status_code}')

    if cities_json:
        return cities_json
    else:
        return None


def get_city_from_json(cities_json, index):
    city_name = cities_json[index].get('name')
    state = cities_json[index].get('state', '')
    country = cities_json[index].get('country')
    _lat = cities_json[index].get('lat')
    _lon = cities_json[index].get('lon')
    return {
        'city_name': city_name,
        'state': state,
        'country': country,
        'lat': _lat,
        'lon': _lon,
    }


def get_forecast_json(_lat, _lon):
    forecast_url = f'https://api.openweathermap.org/data/2.5/onecall?lat={_lat}&lon={_lon}&exclude=minutely,hourly&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru'
    forecast_response = requests.get(forecast_url)

    if forecast_response.status_code == 200:
        _forecast_json = json.loads(forecast_response.text)
    else:
        sys.exit(f'⚠ Ошибка: Status Code {forecast_response.status_code}')
    return _forecast_json


@dp.message_handler(commands='help')
async def start(message: types.Message):
    await message.answer('Введите название города:')


@dp.message_handler()
async def get_city(message: types.Message):
    city = message.text
    cities_json = get_cities_json(city)
    if cities_json:
        buttons = []
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=True, row_width=1)
        for i in range(len(cities_json)):
            c = get_city_from_json(cities_json, i)
            btn = types.InlineKeyboardButton(text=f"{c.get('city_name')} - ({c.get('country')}), {c.get('state')}",
                                             callback_data=f"{c.get('lat')} {c.get('lon')}",
                                             )
            buttons.append(btn)
        keyboard.add(*buttons)

        await message.answer('Уточните город:', reply_markup=keyboard)
    else:
        await message.answer('⚠ Город не найден ⚠')  # .reply('Город не найден')


@dp.callback_query_handler(lambda callback_query: True)
async def forecast(callback_query: types.CallbackQuery):
    lat, lon = callback_query.data.split(' ')
    forecast_json = get_forecast_json(lat, lon)
    current_weather = forecast_json['current']

    local_timezone = tzlocal.get_localzone()
    local_time = dt.datetime.fromtimestamp(float(current_weather['dt']), local_timezone)

    current_card = f"{hbold('Текущая погода:')}\n" \
                   f"{local_time.strftime('%d/%m/%Y %H:%M')} {DAYS_OF_WEEK[local_time.weekday()]} \n" \
                   f"Температура: {round(current_weather['temp'])}°C, {current_weather['weather'][0]['description'].title()}\n" \
                   f"Влажность: {current_weather['humidity']}%\n" \
                   f"Давление: {current_weather['pressure']} мм.рт.ст.\n" \
                   f"Ветер: {current_weather['wind_speed']} м/с"

    await callback_query.message.answer(current_card)

    forecast_daily = forecast_json['daily']

    for day in forecast_daily[1:4]:  # Пропускаю первый день - это текущая погода, показанная ранее.
        # Ограничил прогноз тремя днями. Иначе получается стена текста,
        current_date = dt.datetime.fromtimestamp((float(day['dt'])))
        forecast_card = f"{hbold(current_date.strftime('%d/%m/%Y'))} " \
                        f"{hbold(DAYS_OF_WEEK[current_date.weekday()])}\n" \
                        f"Температура: {round(day['temp']['night'])}...{round(day['temp']['day'])}°C,\n" \
                        f"{day['weather'][0]['description'].title()}\n" \
                        f"Влажность: {day['humidity']}%\n" \
                        f"Давление: {day['pressure']} мм.рт.ст.\n" \
                        f"Ветер: {day['wind_speed']} м/с"

        await callback_query.message.answer(forecast_card)


def main():
    executor.start_polling(dp)


if __name__ == '__main__':
    main()
