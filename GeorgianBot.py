#!/usr/bin/env python
# coding: utf-8


import os

from google.cloud import translate_v2 as translate
from telegram.ext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.filters import Filters
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.updater import Updater
from telegram.update import Update
from transliterate import translit

in_game = False
is_finished = False
correct_number = -1
attempts_count = 0


def transliterate_to_ka(message):
    return translit(message, 'ka')


def translate_to_ru(message):
    translate_client = translate.Client()
    transliterated_message = transliterate_to_ka(message)
    result = translate_client.translate(transliterated_message, target_language='ru')
    if result['detectedSourceLanguage'] == 'ka':
        return result['translatedText']
    else:
        languages = translate_client.get_languages()
        detected_language = list(filter(lambda x: x['language'] == result['detectedSourceLanguage'], languages))[0][
            'name']
        return "Извините, распознан язык сообщения: " + detected_language + ". Бот работает только с текстом на " \
                                                                            "грузинском языке "


def is_correct_twenty_based(number, prefixes):
    if "ოცი" not in number:
        return -1
    prefix = number.split("ოცი")
    if prefix[0] in prefixes:
        return 1
    else:
        return -1


def is_correct_composed_number(number, first_numbers, prefixes):
    if "ოცდა" not in number:
        return is_correct_twenty_based(number, prefixes)
    else:
        parts = number.split("ოცდა")
        if (parts[0] == '' or parts[0] in prefixes) and parts[1] in first_numbers:
            return 2
        else:
            return -1


def is_correct_one_part_number(number, first_numbers, special_one_part_numbers):
    if number in first_numbers or number in special_one_part_numbers:
        return 0
    else:
        return -1


def is_correct_number(input_str, first_numbers, special_numbers, prefixes):
    if not (input_str and input_str.strip()):
        return -1
    number = input_str.strip()
    one_part_code = is_correct_one_part_number(number, first_numbers, special_numbers)
    if one_part_code == 0:
        return one_part_code
    else:
        return is_correct_composed_number(number, first_numbers, prefixes)


def map_one_part_number(number, first_numbers, specials=None):
    if specials is None:
        specials = {}
    if number in first_numbers.keys():
        return first_numbers[number]
    else:
        return specials[number]


def map_twenty_based_number(number, prefixes):
    parts = number.split("ოცი")
    return prefixes[parts[0]]


def map_composed_number(number, first_numbers, prefixes):
    parts = number.split("ოცდა")
    if parts[0] != '':
        pref = map_twenty_based_number(parts[0], prefixes)
    else:
        pref = 20
    first_number = map_one_part_number(parts[1], first_numbers)
    return pref + first_number


def word_to_number(input_str):
    first_numbers_map = {
        "ერთი": 1,
        "ორი": 2,
        "სამი": 3,
        "ოთხი": 4,
        "ხუთი": 5,
        "ექვსი": 6,
        "შვიდი": 7,
        "რვა": 8,
        "ცხრა": 9,
        "ათი": 10,
        "თერთმეტი": 11,
        "თორმეტი": 12,
        "ცამეტი": 13,
        "თოთხმეტი": 14,
        "თხუთმეტი": 15,
        "თექვსმეტი": 16,
        "ჩვიდმეტი": 17,
        "თვრამეტი": 18,
        "ცხრამეტი": 19
    }

    prefixes_map = {
        "ორმ": 40,
        "სამ": 60,
        "ოთხმ": 80
    }

    specials_map = {
        "ოცი": 20,
        "ასი": 100
    }

    first_numbers = list(first_numbers_map.keys())
    specials = list(specials_map.keys())
    prefixes = list(prefixes_map.keys())
    response = is_correct_number(input_str, first_numbers, specials, prefixes)
    if response == -1:
        return -1
    elif response == 0:
        return map_one_part_number(input_str.strip(), first_numbers_map, specials_map)
    elif response == 1:
        return map_twenty_based_number(input_str.strip(), prefixes_map)
    elif response == 2:
        return map_composed_number(input_str.strip(), first_numbers_map, prefixes_map)


def generate(low_limit, high_limit):
    import random
    return random.randint(low_limit, high_limit)


def game_round(update, true_number, inp):
    global attempts_count
    mapped_number = word_to_number(inp)
    attempts_count += 1
    if mapped_number == -1:
        update.message.reply_text("ეს არაა რიცხვი. დაწერეთ რიცხვი სიტყვებით (Это не число. Напишите число словами)")
        return False
    elif mapped_number < true_number:
        update.message.reply_text("არა, რიცხვი თკვენზე მეტია (Нет, число больше твоего)")
        return False
    elif mapped_number > true_number:
        update.message.reply_text("არა, რიცხვი თკვენზე ნაკლებია (Нет, число меньше твоего)")
        return False
    else:
        update.message.reply_text("სწორად (верно)!")
        update.message.reply_text("მცდელობების რაოდენობა (Количество попыток): " + str(attempts_count))
        return True


def start(update: Update, context: CallbackContext):
    update.message.reply_text(("გამარჯობა! Я могу выполнять перевод с грузинского языка на русский, "
                               "просто отправьте мне сообщение на грузинском языке! "
                               " Также Вы можете играть в 'Угадай число от 1 до 100' на грузинском"
                               " языке для запоминания чисел на грузинском."
                               " Инструкцию можно получить с помощью /help"))


def get_help(update: Update, context: CallbackContext):
    update.message.reply_text(("Бот имеет две функции: перевод текста с грузинского на русский"
                               " и игра 'Угадай число от 1 до 100' на грузинском языке."
                               " При выборе команды /play начнется игра. При выборе команды "
                               "/stop игра будет остановлена. Передавать текст для перевода "
                               "можно вне режима игры: когда она завершена или остановлена"))


def stop(update: Update, context: CallbackContext):
    global in_game
    global is_finished
    global correct_number
    global attempts_count
    in_game = False
    is_finished = False
    correct_number = -1
    attempts_count = 0
    update.message.reply_text("Игра остановлена")


def translate_command(update: Update, context: CallbackContext):
    update.message.reply_text(translate_to_ru(update.message.text))


def unknown(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Извините, введена невалидная команда. Бот принимает команды /start, /help, /play, /stop")


def play_game(update: Update, context: CallbackContext):
    global in_game
    global is_finished
    global correct_number
    global attempts_count
    in_game = True
    correct_number = generate(1, 101)
    update.message.reply_text('თამაში "გამოიცანით რიცხვი 1-დან 100-მდე” (Игра "Угадайте число от 1 до 100")')
    update.message.reply_text("დაწერეთ რიცხვი სიტყვებით (Напишите число словами):")
    is_finished = False
    attempts_count = 0


def switch_mode(update: Update, context: CallbackContext):
    global in_game
    global is_finished
    global correct_number
    global attempts_count
    if in_game:
        is_finished = game_round(update, correct_number, update.message.text)
        if is_finished:
            update.message.reply_text("Игра завершена")
            in_game = False
            correct_number = -1
            attempts_count = 0
    else:
        translate_command(update, context)


if __name__ == '__main__':
    assert (token := os.environ.get('TOKEN')), 'Пожалуйста, укажите переменную окружения TOKEN'

    updater = Updater(token, use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', get_help))
    updater.dispatcher.add_handler(CommandHandler('play', play_game))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, switch_mode))
    updater.dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
