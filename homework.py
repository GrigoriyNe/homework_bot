import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telebot import TeleBot


load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    filemode='w',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('my_logger.log',
                              maxBytes=50000000,
                              backupCount=5
                              )
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Check validity all tokens."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True

def send_message(bot, message):
    """Send messages and check validity messages."""
    try:
        bot.send_message(
            TELEGRAM_CHAT_ID,
            message
        )
        logger.debug('Отправленно в чат {TELEGRAM_CHAT_ID} : {message}')
    except Exception:
        logger.error('Ошибка отправки в чат {TELEGRAM_CHAT_ID} : {message}')
        raise Exception('Ошибка отправки в чат {TELEGRAM_CHAT_ID} : {message}')


def get_api_answer(timestamp):
    """."""
    params = {'from_date': timestamp}
    try:
        homework_answer = requests.get(ENDPOINT,
                                       headers=HEADERS,
                                       params=params
                                       )
    except TypeError:
        logger.error(
            'Ошибка при запросе к API: - не верная timestamp'
        )
        raise TypeError(
            'Ошибка при запросе к API: - не верная timestamp'
        )
    except Exception as error:
        logger.error(f'Ошибка при запросе к API:{error}')
        raise Exception(f'Ошибка при запросе к API:{error}')

    if homework_answer.status_code != HTTPStatus.OK:
        logger.error(f'Ошибка ответа - {homework_answer}')
        raise Exception(f'Ошибка ответа - {homework_answer}')
    try:
        logger.info('json сформирован успешно')
        return homework_answer.json()
    except Exception:
        logger.error('Ошибка при формировании json')
        raise Exception('Ошибка при формировании json')


def check_response(response):
    """."""
    if type(response) != dict:
        logger.error('В ответе API - не словарь')
        raise TypeError('В ответе API - не словарь')
    try:
        homework_list = response['homeworks']
    except TypeError:
        logger.error('В словаре нет ключа homeworks')
        raise TypeError('В словаре нет ключа homeworks')
    try:
        homework = homework_list[0]
    except IndexError:
        logger.error('В словаре нет домашних работ')
        raise IndexError('В словаре нет домашних работ')
    return homework


def parse_status(homework):
    """Generate answer on chat."""
    if 'homework_name' not in homework:
        logger.debug('В словаре нет ключа homework_name')
        raise KeyError('В словаре нет ключа homework_name')
    if 'status' not in homework:
        logger.error('В словаре нет ключа status')
        raise KeyError('В словаре нет ключа status')
    homework_name = homework['homework_name']
    homework_verdict = homework['status']
    if homework_verdict not in HOMEWORK_VERDICTS:
        logger.error('Неопознанный вердикт - {homework_verdict}')
        raise KeyError('Неопознанный вердикт - {homework_verdict}')
    verdict = HOMEWORK_VERDICTS[homework_verdict]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Main cycle of bot.
    Status и error_message defined in beginning of the function.
    When cycle is running, not send repeated messages.
    """
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 1800000
    cash_message = ''
    cash_error_message = ''
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise Exception('Отсутствуют одна или несколько переменных окружения')
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != cash_message:
                send_message(bot, message)
                cash_message = message
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message_error = f'Сбой в работе программы: {error}'
            logger.error(f'Сбой в работе программы: {error}')
            if message_error != cash_error_message:
                send_message(bot, message_error)
                cash_error_message = message_error
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
