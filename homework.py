import logging
import os
import requests
from sys import exit
import time
from http import HTTPStatus

from dotenv import load_dotenv

import telegram
from telegram.ext import CommandHandler, Updater

from loggers import logger, formatter

LOG_NAME = 'PracticumStatusBot.log'

file_handler = logging.FileHandler(LOG_NAME)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

load_dotenv()

PRACTICUM_TOKEN = os.getenv(
    'YANDEX_TOKEN',
    default='AQAABAABaT4WcAYckdSYm5vyn27g8TKtITc'
)

TELEGRAM_TOKEN = os.getenv(
    'TELEGRAM_TOKEN',
    default='3174677406:AAHx7ijkmekXILBbfYzn7nAaNqtiQjU63q8'
)

TELEGRAM_CHAT_ID = os.getenv(
    'USER_ID',
    default='123896774'
)

try:
    BOT = telegram.Bot(token=TELEGRAM_TOKEN)
except TypeError:
    logger.critical('Обязательная переменная окружения '
                    'TELEGRAM_TOKEN отсутствует либо неверная.')
    exit()

EPOCH_TIME_FOR_REQUEST_LATEST = 1638230400  # The beginning of 2022
LAST_TIMESTAMP = 0  # Time of last hw checking
RETRY_TIME = 600  # in seconds
PRACTICUM_ENDPOINT = ('https://practicum.yandex.ru/api/'
                      'user_api/homework_statuses/')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Send a telegram message to the chat with the given ID."""
    button = telegram.ReplyKeyboardMarkup(
        [['/request_latest']], resize_keyboard=True
    )
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            reply_markup=button
        )
    except Exception as error:
        logger.error(f'Боту не удалось отправить сообщение. '
                     f'Ошибка: {error}')
    else:
        logger.info(f'Бот отправил сообщение с текстом: {message}')


def get_api_answer(last_timestamp: int):
    """Connect to Yandex.Practicum API and refresh homework statuses."""
    params = {'from_date': last_timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    homework_statuses = requests.get(
        PRACTICUM_ENDPOINT,
        headers=headers,
        params=params,
    )
    if homework_statuses.status_code == HTTPStatus.OK:
        homework_statuses = homework_statuses.json()
        return homework_statuses
    else:
        logger.error(f'Сбой в работе программы при попытке '
                      f'доступа к эндпоинту {PRACTICUM_ENDPOINT}.'
                      f'Код ответа API: {homework_statuses.status_code}')
        raise ValueError


def check_response(response: dict):
    """Checking if data from Yandex is correct."""
    if not isinstance(response, dict):
        response_type = type(response)
        logger.error(f'Ошибка формата данных Yandex. Вместо типа dict'
                      f'в ответе объект типа {response_type}')
        raise TypeError
        # checking if there is a list with 'homeworks' key
    if not isinstance(response.get('homeworks'), list):
        homework_type = type(response.get('homeworks'))
        logger.error(f'Ошибка формата данных Yandex. '
                      f'По ключу \'homeworks\' вместо типа list'
                      f'расположен объект типа {homework_type}')
        raise TypeError
    return response.get('homeworks')


def parse_status(homework: dict):
    """Parse latest change in homework status."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError as error:
        logger.error(f'В ответе API недокументированный статус '
                      f'домашней работы: {error}')
        raise KeyError
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Checking if all the tokens required for bot are available in .env."""
    if not PRACTICUM_TOKEN:
        return 'PRACTICUM_TOKEN'
    elif not TELEGRAM_TOKEN:
        return 'TELEGRAM_TOKEN'
    elif not TELEGRAM_CHAT_ID:
        return 'TELEGRAM_CHAT_ID'
    return True


def say_hi(update, context):
    """Initial greeting and render 'refresh' button."""
    text = 'Yo my dude!'
    send_message(BOT, text)
    text = 'Hope you\'re having a nice day!'
    send_message(BOT, text)


def request_latest(update, context):
    """Check status of the latest homework."""
    try:
        yandex_response = get_api_answer(EPOCH_TIME_FOR_REQUEST_LATEST)
        homework_list = check_response(yandex_response)
    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        logger.error(message)
        send_message(BOT, message)
    else:
        text = parse_status(homework_list[0])
        send_message(BOT, text)


def main():
    """Bot main logic."""
    last_timestamp = 0  # initial time of the latest request

    tokens_status = check_tokens()  # check tokens status
    if isinstance(tokens_status, str):
        logger.critical(f'Отсутствует обязательная '
                        f'переменная окружения {tokens_status}.')
        exit()

    updater = Updater(token=TELEGRAM_TOKEN)

    updater.dispatcher.add_handler(CommandHandler('start', say_hi))
    updater.dispatcher.add_handler(CommandHandler(
        'request_latest',
        request_latest,
    ))

    while True:
        logger.debug('last_timestamp = ')
        logger.debug(last_timestamp)
        logger.debug('***WHILE LOOP***')
        try:
            yandex_response = get_api_answer(last_timestamp)
            homework_list = check_response(yandex_response)
            try:
                text = parse_status(homework_list[0])
            except IndexError:
                logger.info('Нет обновлений статуса '
                              'для последней домашней работы.')
            else:
                send_message(BOT, text)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        else:
            last_timestamp = int(time.time())  # refresh timestamp
        finally:
            updater.start_polling(poll_interval=0.0)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
