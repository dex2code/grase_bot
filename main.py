import telebot
import requests
import os
import sys
import translators.server as tss
import wikipediaapi
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv


'''
Подгружаем токен из .env и стартуем бота
'''
try:
    load_dotenv(".env")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    bot = telebot.TeleBot(BOT_TOKEN)
except Exception as E:
    logger.error(f"Ошибка при старте бота: 'str({E})'")
    sys.exit()

logger.info(f"Стартовали бота: {bot}")


"""
Устанавливаем меню бота
"""
try:
    bot.set_my_commands([
        telebot.types.BotCommand("/help", "Команды бота"),
        telebot.types.BotCommand("/day",  "События дня"),
        telebot.types.BotCommand("/wiki", "Узнать значение в WikiPedia")
    ])
except Exception as E:
    logger.error(f"Ошибка при установке меню бота: 'str({E})'")
    sys.exit()

logger.info(f"Установили команды бота.")


"""
Подключаем Wikipedia
"""
try:
    wiki = wikipediaapi.Wikipedia('ru')
except Exception as E:
    logger.error(f"Ошибка при подключении Wikipedia: 'str({E})'")
    sys.exit()

logger.info(f"Подключили Wikipedia.")




@bot.message_handler(commands=["start"])
@logger.catch
def bot_start(message):
    """
    Функция Start - начало работы с ботом
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    answer = f"Привет, <b>{message.from_user.first_name}</b> ✌ \n\nЧтобы узнать все команды бота: /help\n"
    bot.send_message(chat_id=message.chat.id, text=answer, parse_mode='html')


@bot.message_handler(commands=["help"])
@logger.catch
def bot_help(message):
    """
    Функция Help - вывод информации о боте
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    answer = f"""
    <b>Grase BOT</b> - это умный помощник для поиска ответов на вопросы:

    - События этого дня: <b>/day</b>

    - Информация в <i>Wikipedia</i>: <b>/wiki</b>

    - Перевести на <i>Русский</i>: <b>/tr_rus</b>

    - Перевести на <i>English</i>: <b>/tr_eng</b>

    Связаться с создателем бота: @kmmax
    """
    bot.send_message(chat_id=message.chat.id, text=answer, parse_mode='html')


@bot.message_handler(commands=["day"])
@logger.catch
def day(message):
    """
    Функция Day - узнать информацию про сегодняшний день
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    cur_date = datetime.now()

    cur_day   = str(cur_date.day).zfill(2)
    cur_month = str(cur_date.month).zfill(2)

    api_url = f"http://numbersapi.com/{cur_month}/{cur_day}/date"

    try:
        api_res = requests.get(url=api_url, timeout=10)
    except Exception:
        api_res_text_eng = "<b>Ошибка!</b> Сервер недоступен!"
    else:
        if api_res and api_res.status_code == 200:
            api_res_text_eng = api_res.text
        else:
            api_res_text_eng = f"<b>Ошибка!</b> Сервер вернул ошибку ({str(api_res.status_code)})!"

    try:
        api_res_text_rus = tss.google(query_text=api_res_text_eng, to_language='ru')
    except Exception:
        api_res_text_rus = ""

    if api_res_text_rus:
        answer = f"Вот интересный факт про сегодняшний день: <i>" + api_res_text_rus + "</i>\n /day "
    else:
        answer = f"Вот интересный факт про сегодняшний день (к сожалению, перевод временно не работает): <i>" + api_res_text_eng  + "</i>\n /day "

    bot.send_message(chat_id=message.chat.id, text=answer, parse_mode='html')


@bot.message_handler(commands=["wiki"])
@logger.catch
def bot_wiki(message):
    """
    Функция Wiki - регистрирует обработчик для следующего введенного слова
    """
    logger.info(f"{datetime.now()} - Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    user_msg = bot.send_message(message.chat.id, "Введите слово, значение которого вы хотите найти в Wikipedia:" )
    bot.register_next_step_handler(user_msg, bot_wiki_parse)

@logger.catch
def bot_wiki_parse(message):
    """
    Функция Parse Wiki - Ищет введенное слово в википедии и возвращает значение
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    user_request = str(message.text)
    user_request = user_request.strip()

    bot.send_message(message.chat.id, f"Вы хотели найти '<i>{user_request}</i>'", parse_mode='html')

    wiki_page = wiki.page(user_request)

    if wiki_page.exists():
        page_sum = wiki_page.summary[0:1024]
        page_sum = page_sum.split(" ")[:-1]
        page_sum = " ".join(page_sum) + "..."
        bot.send_message(message.chat.id, f"{page_sum}", parse_mode='html')
        bot.send_message(message.chat.id, f"Узнать больше тут: {wiki_page.fullurl}", parse_mode='html')
        bot.send_message(message.chat.id, f"Еще один запрос: /wiki", parse_mode='html')
    else:
        bot.send_message(message.chat.id, f"К сожалению, по вашему запросу ничего не найдено. Попробуйте указать другое слово, после команды /wiki", parse_mode='html')


if __name__ == "__main__":
    logger.info("Начинаем цикл обработки команд...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
