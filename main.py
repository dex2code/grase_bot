import os
import sys
from datetime import datetime

import requests
import telebot
import translators.server as tss
import wikipediaapi
from dotenv import load_dotenv
from loguru import logger


"""
Добавляем лог-файл
"""
logger.add("main.log", format="{time} -- {level} -- {message}", level="DEBUG", rotation="1 week", compression="zip")
logger.info(f"***")
logger.info(f"Grase Telegram bot starting service...")

"""
Подгружаем токен из .env и стартуем бота
"""
try:
    load_dotenv(dotenv_path=".env")
    BOT_TOKEN = os.getenv(key="BOT_TOKEN")
    bot = telebot.TeleBot(token=BOT_TOKEN)
except Exception as E:
    logger.error(f"Ошибка при старте бота: 'str({E})'")
    sys.exit()

logger.info(f"Стартовали бота: {bot}")


"""
Устанавливаем меню бота
"""
try:
    bot.set_my_commands([
        telebot.types.BotCommand(command="/help",     description="Команды бота"),
        telebot.types.BotCommand(command="/day",      description="События дня"),
        telebot.types.BotCommand(command="/wiki",     description="Узнать значение в WikiPedia"),
        telebot.types.BotCommand(command="/tr_rus",   description="Перевести на Русский"),
        telebot.types.BotCommand(command="/tr_eng",   description="Перевести на English"),
        telebot.types.BotCommand(command="/boring",   description="Мне скучно! Что делать?"),
        telebot.types.BotCommand(command="/yesno",    description="У меня важный вопрос! Да или Нет?"),
        telebot.types.BotCommand(command="/show_id",  description="Показать ваш ID и ID чата")
    ])
except Exception as E:
    logger.error(f"Ошибка при установке меню бота: 'str({E})'")
    sys.exit()

logger.info(f"Установили команды бота.")


"""
Подключаем Wikipedia
"""
try:
    wiki = wikipediaapi.Wikipedia(language="ru")
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

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Привет, <b>{message.from_user.first_name}</b> ✌ \n\nЧтобы узнать все команды бота: /help\n",
        parse_mode="html"
    )


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

    - Мне скучно! Что делать: <b>/boring</b>

    - У меня важный вопрос! <i>Да или Нет</i>: <b>/yesno</b>

    - Покажи мне <i>ID</i> - мой и текущего чата: <b>/show_id</b>

    Связаться с создателем бота: @kmmax
    """
    bot.send_message(chat_id=message.chat.id, text=answer, parse_mode="html")


@bot.message_handler(commands=["day"])
@logger.catch
def day(message):
    """
    Функция Day - узнать информацию про сегодняшний день
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    cur_date  = datetime.now()
    cur_day   = str(object=cur_date.day).zfill(2)
    cur_month = str(object=cur_date.month).zfill(2)

    api_url = f"http://numbersapi.com/{cur_month}/{cur_day}/date"

    try:
        api_res = requests.get(url=api_url, timeout=10)
    except Exception as E:
        api_res_text_eng = "<b>Ошибка!</b> Сервер недоступен!"
        logger.error(f"Ошибка при получении данных от сервиса: ({str(E)})")
    else:
        if api_res and api_res.status_code == 200:
            api_res_text_eng = api_res.text
        else:
            api_res_text_eng = f"<b>Ошибка!</b> Сервер вернул ошибку ({str(api_res.status_code)})!"

    try:
        api_res_text_rus = tss.google(query_text=api_res_text_eng, to_language="ru")
    except Exception as E:
        api_res_text_rus = ""
        logger.error(f"Ошибка при переводе строки: ({str(E)})")

    if api_res_text_rus:
        answer = f"""
        Вот интересный факт про сегодняшний день:

        - <i>{api_res_text_rus}</i>

        Еще один факт: /day
        """
    else:
        answer = f"""
        Вот интересный факт про сегодняшний день (к сожалению, перевод временно не работает):

        - <i>{api_res_text_eng}</i>

        Еще один факт: /day
        """

    bot.send_message(chat_id=message.chat.id, text=answer, parse_mode="html")


@bot.message_handler(commands=["wiki"])
@logger.catch
def bot_wiki(message):
    """
    Функция Wiki - регистрирует обработчик для следующего введенного слова
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    user_msg = bot.send_message(
        chat_id=message.chat.id,
        text="Введите слово, значение которого вы хотите найти в <b>Wikipedia</b>:",
        parse_mode="html"
    )

    bot.register_next_step_handler(message=user_msg, callback=bot_wiki_parse)

@logger.catch
def bot_wiki_parse(message):
    """
    Функция Wiki_Parse - ищет введенное слово в википедии и возвращает значение
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    user_request = str(object=message.text)
    user_request = user_request.strip()

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Вы хотите найти: '<i>{user_request}</i>'",
        parse_mode="html"
    )

    wiki_page = wiki.page(title=user_request)

    if wiki_page.exists():
        page_sum = wiki_page.summary[0:1024]
        page_sum = page_sum.split(" ")[:-1]
        page_sum = " ".join(page_sum) + "..."
        bot.send_message(chat_id=message.chat.id, text=f"{page_sum}", parse_mode="html")
        bot.send_message(chat_id=message.chat.id, text=f"Узнать больше тут: {wiki_page.fullurl}", parse_mode="html")
        bot.send_message(chat_id=message.chat.id, text=f"Еще один запрос: /wiki", parse_mode="html")
    else:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"К сожалению, по вашему запросу ничего не найдено. Попробуйте указать другое слово после команды /wiki",
            parse_mode="html"
        )


@bot.message_handler(commands=["tr_rus"])
@logger.catch
def bot_tr_rus(message):
    """
    Функция Translate to Russian - регистрирует обработчик для следующего введенного слова
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    user_msg = bot.send_message(
        chat_id=message.chat.id,
        text="Введите слово или фразу, которую вы хотите перевести <b>на Русский язык</b>:",
        parse_mode="html"
    )

    bot.register_next_step_handler(message=user_msg, callback=bot_tr_rus_parse)

@logger.catch
def bot_tr_rus_parse(message):
    """
    Функция Translate to Russian Parse - переводит слово и пишет в чат полученный перевод
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    user_request = str(object=message.text)
    user_request = user_request.strip()

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Вы хотите перевести <b>на Русский язык</b>: '<i>{user_request}</i>'",
        parse_mode="html"
    )

    try:
        translated_rus = tss.google(query_text=user_request, to_language="ru")
    except Exception as E:
        bot.send_message(chat_id=message.chat.id, text=f"К сожалению, перевод временно не работает.\n Попробуйте еще раз: /tr_rus", parse_mode="html")
        logger.error(f"Ошибка при переводе строки: ({str(E)})")

    bot.send_message(chat_id=message.chat.id, text=f"Перевод: <i>'{translated_rus}'</i>", parse_mode="html")
    bot.send_message(chat_id=message.chat.id, text=f"Перевести еще: <b>/tr_rus</b>", parse_mode="html")


@bot.message_handler(commands=["tr_eng"])
@logger.catch
def bot_tr_eng(message):
    """
    Функция Translate to English - регистрирует обработчик для следующего введенного слова
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    user_msg = bot.send_message(
        chat_id=message.chat.id,
        text="Введите слово или фразу, которую вы хотите перевести <b>на English</b>:",
        parse_mode="html"
    )

    bot.register_next_step_handler(message=user_msg, callback=bot_tr_eng_parse)

@logger.catch
def bot_tr_eng_parse(message):
    """
    Функция Translate to English Parse - переводит слово и пишет в чат полученный перевод
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    user_request = str(object=message.text)
    user_request = user_request.strip()

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Вы хотите перевести <b>на English</b>: '<i>{user_request}</i>'",
        parse_mode="html"
    )

    try:
        translated_eng = tss.google(query_text=user_request, to_language="en")
    except Exception as E:
        bot.send_message(chat_id=message.chat.id, text=f"К сожалению, перевод временно не работает.\n Попробуйте еще раз: /tr_eng", parse_mode="html")
        logger.error(f"Ошибка при переводе строки: ({str(E)})")

    bot.send_message(chat_id=message.chat.id, text=f"Перевод: <i>'{translated_eng}'</i>", parse_mode="html")
    bot.send_message(chat_id=message.chat.id, text=f"Перевести еще: <b>/tr_eng</b>", parse_mode="html")


@bot.message_handler(commands=["boring"])
@logger.catch
def bot_boring(message):
    """
    Функция Boring - Ответ на вопрос, что делать, если скучно.
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    api_url = f"https://www.boredapi.com/api/activity/"

    try:
        api_res = requests.get(url=api_url, timeout=10)
    except Exception as E:
        api_res_text_eng = "<b>Ошибка!</b> Сервер недоступен!"
        logger.error(f"Ошибка при получении данных от сервиса: ({str(E)})")
    else:
        if api_res and api_res.status_code == 200:
            api_res_json = api_res.json()
            api_res_text_eng = api_res_json["activity"]
        else:
            api_res_text_eng = f"<b>Ошибка!</b> Сервер вернул ошибку ({str(api_res.status_code)})!"

    try:
        api_res_text_rus = tss.google(query_text=api_res_text_eng, to_language="ru")
    except Exception as E:
        api_res_text_rus = ""
        logger.error(f"Ошибка при переводе строки: ({str(E)})")

    if api_res_text_rus:
        answer = f"""
        Вот интересное занятие, если вам скучно:

        - <i>{api_res_text_rus}</i>

        """
    else:
        answer = f"""
        Вот интересное занятие, если вам скучно (к сожалению, перевод временно не работает):

        - <i>{api_res_text_eng}</i>

        """

    bot.send_message(chat_id=message.chat.id, text=answer, parse_mode="html")

    if api_res_json["link"]:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Узнать больше: {api_res_json['link']}",
            parse_mode="html"
        )
    
    bot.send_message(chat_id=message.chat.id, text="Мне не подходит, что есть еще: /boring", parse_mode="html")


@bot.message_handler(commands=["yesno"])
@logger.catch
def bot_yesno(message):
    """
    Функция YesNo - Ответ на вопрос, Да или Нет.
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")

    api_url = f"https://yesno.wtf/api"

    try:
        api_res = requests.get(url=api_url, timeout=10)
    except Exception as E:
        api_res_text = "<b>Ошибка!</b> Сервер недоступен!"
        logger.error(f"Ошибка при получении данных от сервиса: ({str(E)})")
    else:
        if api_res and api_res.status_code == 200:
            api_res_json = api_res.json()
            api_res_text = api_res_json["answer"]
            api_res_url  = api_res_json["image"]
        else:
            api_res_text = f"<b>Ошибка!</b> Сервер вернул ошибку ({str(api_res.status_code)})!"
            api_res_url  = ""
    
    bot.send_message(chat_id=message.chat.id, text=api_res_url, parse_mode="html")
    bot.send_message(chat_id=message.chat.id, text="Еще разок: /yesno", parse_mode="html")


@bot.message_handler(commands=["show_id"])
@logger.catch
def bot_show_id(message):
    """
    Функция Show ID - Отвечает ID пользователя и чата.
    """
    logger.info(f"Получен запрос '{message.text}' от пользователя '{message.from_user.id}'")
    
    bot.send_message(
        chat_id=message.chat.id,
        text=f"""
        Ваши ID:
        - <b>ID пользователя</b>: <i>{message.from_user.id}</i>
        - <b>ID чата</b>: <i>{message.chat.id}</i>
        """,
        parse_mode="html"
    )


if __name__ == "__main__":
    logger.info("Начинаем цикл обработки команд...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
