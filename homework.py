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
    # default='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
)

TELEGRAM_TOKEN = os.getenv(
    'TELEGRAM_TOKEN',
    # default='1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAA-AAAAAAA'
)

TELEGRAM_CHAT_ID = os.getenv(
    'USER_ID',
    # default="11111111"
)

try:
    BOT = telegram.Bot(token=TELEGRAM_TOKEN)
except TypeError:
    logger.critical('Обязательная переменная окружения '
                    'TELEGRAM_TOKEN отсутствует либо неверная.')
    exit()

EPOCH_TIME_FOR_REQUEST_LATEST = 1638230400  # The beginning of 2022
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
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as error:
        logger.error(f'Боту не удалось отправить сообщение. '
                     f'Ошибка: {error}')
    else:
        logger.info(f'Бот отправил сообщение с текстом: {message}')


def get_api_answer(current_timestamp: int):
    """Connect to Yandex.Practicum API and refresh homework statuses."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
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
                      f'находится тип {response_type}')
        raise TypeError
        # checking if there is a list with 'homeworks' key
    if isinstance(response.get('homeworks'), list):
        homeworks = response.get('homeworks')
        return homeworks
    else:
        homework_type = type(response.get('homeworks'))
        logger.error(f'Ошибка формата данных Yandex. '
                      f'По ключу \'homeworks\' вместо типа list'
                      f'находится тип {homework_type}')
        raise TypeError


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
    logger.debug('say_hi')
    # chat = update.effective_chat
    text = 'Yo my dude!'
    send_message(BOT, text)
    # context.bot.send_message(chat_id=chat.id, text='Yo my dude!')

    button = telegram.ReplyKeyboardMarkup(
        [['/request_latest']], resize_keyboard=True
    )
    text = 'Hope you\'re having a nice day!'
    send_message(BOT, text)

    # context.bot.send_message(
    #     chat_id=TELEGRAM_CHAT_ID,
    #     text='Hope you\'re having a nice day!',
    #     reply_markup=button
    # )


def request_latest(update, context):
    """Check status of the latest homework now."""
    yandex_response = get_api_answer(EPOCH_TIME_FOR_REQUEST_LATEST)
    homework_list = check_response(yandex_response)
    try:
        text = parse_status(homework_list[0])
    except IndexError:
        text = 'Нет обновлений статуса для последней домашней работы.'

    send_message(BOT, text)
    return int(time.time())


def main():
    """Bot main logic."""
    last_timestamp = int(time.time())  # time of the latest request

    logger.debug('last_timestamp = ')
    logger.debug(last_timestamp)

    tokens_status = check_tokens()  # check tokens status
    if isinstance(tokens_status, str):
        logger.critical(f'Отсутствует обязательная '
                        f'переменная окружения {tokens_status}.')
        exit()

    updater = Updater(token=TELEGRAM_TOKEN)

    updater.dispatcher.add_handler(CommandHandler('start', say_hi))
    last_timestamp = updater.dispatcher.add_handler(CommandHandler(
        'request_latest',
        request_latest,
    ))
    logger.debug('last_timestamp = ')
    logger.debug(last_timestamp)

    while True:
        logger.debug('while')
        try:
            yandex_response = get_api_answer(last_timestamp)
            homework_list = check_response(yandex_response)
            try:
                text = parse_status(homework_list[0])
            except IndexError:
                logger.debug('Нет обновлений статуса '
                              'для последней домашней работы.')
            last_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)
        else:
            try:
                send_message(BOT, text)
            except UnboundLocalError:
                pass
        finally:
            updater.start_polling(poll_interval=0.0)


if __name__ == '__main__':
    main()
