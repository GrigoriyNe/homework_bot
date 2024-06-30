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
    bot.send_message(
        TELEGRAM_CHAT_ID,
        message
    )


def get_api_answer(timestamp):
    """."""
    params = {'from_date': timestamp}
    response = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    return response


def check_response(response):
    """."""
    homework_list = response['homeworks']
    return homework_list


def parse_status(homework):
    """Generate answer on chat."""
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
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
            timestamp = response.json().get(
                'current_date', int(time.time())
            )
            if response.status_code != HTTPStatus.OK:
                logger.error(f'Wrong status of answer:{response}')
                raise Exception(f'Ошибка в статусе ответа:{response}')
        except TypeError:
            logger.error('Error answer API: wrorg type')
            raise TypeError('Ошибка ответа API, TypeError')
        except Exception as error:
            logger.error(f'Error answer API:{error}')
            raise Exception(f'Ошибка в ответе API:{error}')
        try:
            homework_list = check_response(response.json())
            if type(homework_list) != list:
                logger.error('Type response don`t lsit')
                raise TypeError('Тип списка домашки - не list')
        except KeyError:
            logger.error('Response don`t have "homeworks"')
            raise KeyError('Ответ не содержит заданий')
        except IndexError:
            logger.error('Homework_list don`t have "homeworks"')
            raise IndexError('В списке домашинх работ нет домашек')
        try:
            message = parse_status(homework_list[0])
            if 'homework_name' not in homework_list[0]:
                logger.debug('List don`t have key "homework_name"')
                raise KeyError('В списке нет ключа "homework_name"')
            if 'status' not in homework_list[0]:
                logger.error('List don`t have key "status"')
                raise KeyError('В списке нет ключа "status"')
            if homework_list[0]['status'] not in HOMEWORK_VERDICTS:
                logger.error('Wrong verdict: {homework_verdict}')
                raise KeyError('Вердикт не определён: {homework_verdict}')
            if message != previous_message:
                try:
                    send_message(bot, message)
                    previous_message = message
                    logger.debug('Success send message')
                except Exception:
                    logger.error(
                        'Error send message {TELEGRAM_CHAT_ID} : {message}'
                    )
        except Exception as error:
            message_error = f'Сбой в работе программы: {error}'
            logger.error(f'Crash of program: {error}')
            if message_error != previous_error_message:
                try:
                    send_message(bot, message_error)
                    previous_error_message = message_error
                except Exception:
                    logger.error(
                        'Error send message {TELEGRAM_CHAT_ID} : {message}'
                    )
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
