import logging
import os
import requests
import time
from http import HTTPStatus

from dotenv import load_dotenv

import telegram
from telegram.ext import CommandHandler, Updater

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

LAST_TIMESTAMP = int(time.time())
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
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


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
        logging.error(f'Сбой в работе программы при попытке '
                      f'доступа к эндпоинту {PRACTICUM_ENDPOINT}.'
                      f'Код ответа API: {homework_statuses.status_code}')
        raise ValueError


def check_response(response: dict):
    """Checking if data from Yandex is correct."""
    if isinstance(response, dict):
        # checking if there is a list with 'homeworks' key
        if isinstance(response.get('homeworks'), list):
            homeworks = response.get('homeworks')
            return homeworks
        else:
            homework_type = type(response.get('homeworks'))
            logging.error(f'Ошибка формата данных Yandex. '
                          f'По ключу \'homeworks\' вместо типа list'
                          f'находится тип {homework_type}')
            raise TypeError
    else:
        response_type = type(response)
        logging.error(f'Ошибка формата данных Yandex. Вместо типа dict'
                      f'находится тип {response_type}')
        raise TypeError


def parse_status(homework: dict):
    """Parse latest change in homework status."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError as error:
        logging.error(f'В ответе API недокументированный статус '
                      f'домашней работы: {error}')
        raise KeyError
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Checking if all the tokens required for bot are available in .env."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def say_hi(update, context):
    """Initial greeting and render 'refresh' button."""
    chat = update.effective_chat
    context.bot.send_message(chat_id=chat.id, text='Yo my dude!')

    button = telegram.ReplyKeyboardMarkup(
        [['/request_now']], resize_keyboard=True
    )

    context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text='Hope you\'re having a nice day!',
        reply_markup=button
    )


def request_now(update, context):
    """Check status of the last homework now."""
    global LAST_TIMESTAMP
    yandex_response = get_api_answer(LAST_TIMESTAMP)
    homework_list = check_response(yandex_response)
    try:
        text = parse_status(homework_list[0])
        try:
            send_message(BOT, text)
            logging.info(f'Бот отправил сообщение с текстом: {text}')
        except Exception as error:
            logging.error(f'Боту не удалось отправить сообщение. '
                          f'Ошибка: {error}')
    except IndexError:
        text = 'Нет обновлений статуса для последней домашней работы.'
        try:
            send_message(BOT, text)
            logging.info(f'Бот отправил сообщение с текстом: {text}')
        except Exception as error:
            logging.error(f'Боту не удалось отправить сообщение. '
                          f'Ошибка: {error}')
    finally:
        LAST_TIMESTAMP = int(time.time())


def main():
    """Bot main logic."""
    global LAST_TIMESTAMP
    if check_tokens():
        updater = Updater(token=TELEGRAM_TOKEN)

        updater.dispatcher.add_handler(CommandHandler('start', say_hi))
        updater.dispatcher.add_handler(CommandHandler(
            'request_now', request_now
        ))

        while True:
            try:
                yandex_response = get_api_answer(LAST_TIMESTAMP)
                homework_list = check_response(yandex_response)
                try:
                    text = parse_status(homework_list[0])
                except IndexError:
                    logging.debug('Нет обновлений статуса '
                                  'для последней домашней работы.')
                LAST_TIMESTAMP = int(time.time())
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(message)
                time.sleep(RETRY_TIME)
            else:
                try:
                    send_message(BOT, text)
                    logging.info(f'Бот отправил сообщение с текстом: {text}')
                except UnboundLocalError:
                    pass
                except Exception as error:
                    logging.error(f'Боту не удалось отправить сообщение. '
                                  f'Ошибка: {error}')
            finally:
                updater.start_polling(poll_interval=1.0)
    else:
        logging.critical('Отсутствует одна из '
                         'обязательных переменных окружения.')


if __name__ == '__main__':
    main()
