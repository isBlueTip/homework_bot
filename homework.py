import logging
import os
import requests
import time
from http import HTTPStatus

from dotenv import load_dotenv

import telegram
from telegram.ext import CommandHandler, Updater, Filters, MessageHandler
# from telegram import ReplyKeyboardMarkup

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='PracticumStatusBot.log',
    filemode='a',
)

PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('USER_ID')
BOT = telegram.Bot(token=TELEGRAM_TOKEN)

ERROR_MESSAGE = 'An error has occurred. Please try again later.'

TEMP_TIME_0 = int(0)  # TODO add function to get timeframe of past 15 or 30 days in seconds from the Epoch
TEMP_TIME_NOW = 1646023025  # TODO add function to get timeframe of past 15 or 30 days in seconds from the Epoch
RETRY_TIME = 600
PRACTICUM_ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Send a telegram message to the chat with given ID."""

    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


def get_api_answer(current_timestamp: int):
    """Connect to Yandex.Practicum API and refresh homework statuses."""

    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    homework_statuses = requests.get(PRACTICUM_ENDPOINT, headers=headers, params=params)
    if homework_statuses.status_code == HTTPStatus.OK:
        homework_statuses = homework_statuses.json()
        return homework_statuses
    else:
        raise ValueError


def check_response(response: dict):
    """Checking if data from Yandex is correct."""

    if isinstance(response, dict):
        if isinstance(response.get('homeworks'), list):  # checking if there is a list with 'homeworks' key
            homeworks = response.get('homeworks')
            return homeworks
        else:
            raise TypeError
    else:
        raise TypeError


def parse_status(homework: dict):
    """Parse latest change in homework status."""

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Checking if all the tokens required for bot
    are available in .env."""

    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def say_hi(update, context):
    """Initial greeting and render 'refresh' button."""

    chat = update.effective_chat
    context.bot.send_message(chat_id=chat.id, text='Yo my dude!')

    button = telegram.ReplyKeyboardMarkup([['/refresh']], resize_keyboard=True)

    context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text='Hope you\'re having a nice day!',
        reply_markup=button
    )


def refresh(update, context):
    yandex_response = get_api_answer(TEMP_TIME_0)

    homework_list = check_response(yandex_response)

    text = parse_status(homework_list[0])
    send_message(BOT, text)


def main():
    """Bot main logic."""

    if check_tokens():
        updater = Updater(token=TELEGRAM_TOKEN)

        updater.dispatcher.add_handler(CommandHandler('start', say_hi))
        updater.dispatcher.add_handler(CommandHandler('refresh', refresh))

        # yandex_response = get_api_answer(TEMP_TIME_0)
        # homework_list = check_response(yandex_response)
        # text = parse_status(homework_list[0])
        # send_message(BOT, text)

        # updater.start_polling(poll_interval=1.0)
        # updater.idle()

        current_timestamp = int(time.time())
        ...
        while True:
            try:
                yandex_response = get_api_answer(current_timestamp)
                homework_list = check_response(yandex_response)
                text = parse_status(homework_list[0])
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(message)
                time.sleep(RETRY_TIME)
            else:
                send_message(BOT, text)






        # ...
        #
        # bot = telegram.Bot(token=TELEGRAM_TOKEN)
        # current_timestamp = int(time.time())

        # ...

        # while True:
        #     try:
        #         response = ...
        #
        #         ...
        #
        #         current_timestamp = ...
        #         time.sleep(RETRY_TIME)
        #
        #     except Exception as error:
        #         message = f'Сбой в работе программы: {error}'
        #         ...
        #         time.sleep(RETRY_TIME)
        #     else:
        #         ...


if __name__ == '__main__':
    main()
