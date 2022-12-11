import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException

from exceptions import StatusCodeException


load_dotenv()

logger = logging.getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """
    Проверяет доступность переменных окружения.
    Возвращает True в случае успеха.
    """
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено.')
    except Exception as error:
        logger.error(f'Сбой в отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except RequestException as err:
        raise StatusCodeException(f'Эндпоинт недоступен: {err}')
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        logger.error('API временно недоступен.')
        raise Exception


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    isinstance(response, dict)
    try:
        hw = response['homeworks']
    except KeyError:
        raise KeyError('Нет ключа homeworks')
    if type(hw) == list:
        return True
    else:
        raise TypeError('homeworks не является списком')


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    Возвращает подготовленную для отправки в Telegram строку.
    """
    try:
        homework.get('status')
    except KeyError:
        raise KeyError('Нет нового статуса')
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise KeyError('Нет ключа домашки')
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        raise KeyError('Нет такого статуса домашки.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует обязательная переменная окружения')
        raise SystemExit('Работа программы завершена')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            try:
                homework = response.get('homeworks')[0]
            except IndexError:
                raise IndexError('Нет домашки для проверки')
            message = parse_status(homework)
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
