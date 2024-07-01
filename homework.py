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
handler = RotatingFileHandler(
    'my_logger.log',
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

FIRST_TIMESTAMP = 0


def check_tokens():
    """Check validity all tokens."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Send messages and check validity messages."""
    try:
        bot.send_message(
            TELEGRAM_CHAT_ID,
            message
        )
        logger.debug('Success send message')
    except Exception:
        logger.error(
            'Error send message {TELEGRAM_CHAT_ID} : {message}'
        )


def get_api_answer(timestamp):
    """Docstring to pass tests.
    The name of the function speaks about the essence
    """
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        raise Exception(f'Ошибка в ответе API:{error}')
    if response.status_code != HTTPStatus.OK:
        raise Exception(f'Ошибка в статусе ответа:{response}')
    return response.json()


def check_response(response):
    """Docstring to pass tests."""
    if (homeworks := response.get('homeworks')) is None:
        raise KeyError('Ответ не содержит заданий')
    if not isinstance(homeworks, list):
        raise TypeError('Тип списка домашки - не list')
    try: 
        homework = homeworks[0] 
    except IndexError: 
        raise IndexError('В списке домашинх работ нет домашек') 
    return homework 


def parse_status(homework):
    """Generate answer on chat."""
    if (homework_name := homework.get('homework_name')) is None:
        logger.debug('Dict don`t have key {homework_name}')
        raise KeyError('В словаре нет ключа {homework_name}')
    if (status := homework.get('status')) is None:
        raise KeyError(f'В словаре нет ключа {status}')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Вердикт не определён: {homework_verdict}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Main cycle of bot.
    Status и error_message defined in beginning of the function.
    When cycle is running, not send repeated messages.
    """
    if not check_tokens():
        logger.critical('One or more environment variables are missing')
        raise Exception('Один или несколько токенов утеряны')
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = FIRST_TIMESTAMP
    previous_message = ''
    previous_error_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            message = parse_status(check_response(response))
            timestamp = response.get(
                timestamp, int(time.time())
            )
            if message == previous_message:
                continue
            send_message(bot, message)
            previous_message = message
        except Exception as error:
            logging.error(error, exc_info=True)
            message_error = f'Сбой в работе программы: {error}'
            if message_error == previous_error_message:
                continue
            send_message(bot, message_error)
            previous_error_message = message_error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
