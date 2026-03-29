import telebot
import random
import re
import os
import requests
from telebot import types
from spellchecker import SpellChecker
from faker import Faker

# Твой токен от BotFather
TOKEN = '8642671012:AAHzT_9RMA-U9bgvL4In4g3BsZoTVTEHnyM'
bot = telebot.TeleBot(TOKEN)

spell = SpellChecker()
fake = Faker('en_US')

WHITELIST = [5453220262, 472339376]
user_history = {}

categories = {
    'final': [],
    'semi': [],
    'city': [],
    'anime': [],
    'actor_imdb': []
}

latin_only = re.compile(r'^[a-zA-Z_]+$')

def is_valid(word):
    return 5 <= len(word) <= 12 and bool(latin_only.match(word))

def load_data():
    print("Загрузка баз...")

    # 1. WORDS
    words_url = "https://raw.githubusercontent.com/ManiacDC/TypingAid/refs/heads/master/Wordlists/Wordlist%20100000%20frequency%20weighted%20(Google%20Books).txt"
    try:
        words_resp = requests.get(words_url).text.splitlines()
        semi_suffixes = ('ed', 'ing', 's', 'es', 'ly', 'ness', 'er', 'est')
        for w in words_resp:
            if is_valid(w):
                w_lower = w.lower()
                if w_lower.endswith(semi_suffixes):
                    categories['semi'].append(w_lower)
                else:
                    categories['final'].append(w_lower)
    except Exception as e:
        print(f"Ошибка слов: {e}")

    # 2. CITIES
    cities_url = "https://raw.githubusercontent.com/lmfmaier/cities-json/refs/heads/master/cities500.json"
    try:
        cities_data = requests.get(cities_url).json()
        for c in cities_data:
            name = c.get('name', '')
            pop = int(c.get('pop', 0))
            if pop >= 100000 and is_valid(name):
                categories['city'].append(name.lower())
    except Exception as e:
        print(f"Ошибка городов: {e}")

    # 3. ANIME (из локального файла anime.txt)
    print("Загрузка anime.txt...")
    if not os.path.exists("anime.txt"):
        print("Файл anime.txt не найден!")
    else:
        try:
            with open("anime.txt", "r", encoding="utf-8") as f:
                for line in f:
                    # Убираем пробелы, чтобы склеить имя и фамилию
                    clean = line.replace(" ", "").strip()
                    if is_valid(clean):
                        categories['anime'].append(clean.lower())
            print(f"Загружено аниме персонажей: {len(categories['anime'])}")
        except Exception as e:
            print(f"Ошибка чтения anime.txt: {e}")

    # 4. STARS (из локального файла stars.txt, ТОЛЬКО АКТЕРЫ)
    print("Загрузка stars.txt...")
    if not os.path.exists("stars.txt"):
        print("Файл stars.txt не найден!")
    else:
        try:
            with open("stars.txt", "r", encoding="utf-8") as f:
                for line in f:
                    # Разбиваем строку по табуляции (как в базе IMDb)
                    parts = line.strip().split("\t")

                    # Проверяем, что колонок достаточно
                    if len(parts) >= 5:
                        name = parts[1]
                        professions = parts[4].lower().split(',')

                        # Строгая проверка: берем ТОЛЬКО если есть 'actor' или 'actress'
                        if 'actor' in professions or 'actress' in professions:
                            # Очищаем имя от спецсимволов и цифр
                            clean = re.sub(r'[^a-zA-Z ]', '', name).strip()
                            words = clean.split()

                            # Склеиваем имя и фамилию
                            if len(words) >= 2:
                                combined = (words[0] + words[1]).lower()
                                if is_valid(combined):
                                    categories['actor_imdb'].append(combined)

            print(f"Загружено актеров: {len(categories['actor_imdb'])}")
        except Exception as e:
            print(f"Ошибка чтения stars.txt: {e}")

    print("Загрузка завершена!")

def check_whitelist(message):
    return message.from_user.id in WHITELIST

@bot.message_handler(commands=['start'], func=check_whitelist)
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Final', 'Semi', 'City')
    markup.add('Name', 'Anime', 'Actors') # Кнопка для актеров
    bot.send_message(message.chat.id, "Выбери категорию:", reply_markup=markup)

@bot.message_handler(func=lambda m: not check_whitelist(m))
def access_denied(message):
    pass

@bot.message_handler(func=lambda m: check_whitelist(m))
def handle_category(message):
    user_id = message.from_user.id
    cat = message.text.lower()

    # Обрабатываем кнопку "Actors", связывая её с категорией базы
    if cat == 'actors':
        cat = 'actor_imdb'

    if user_id not in user_history:
        user_history[user_id] = set()

    # Генерация имен через Faker
    if cat == 'name':
        final_word = None
        for _ in range(150):
            w = fake.first_name().lower()
            if is_valid(w) and w not in user_history[user_id]:
                final_word = w
                break
        if not final_word:
            final_word = fake.first_name().lower() # Фолбэк, если всё перебрали

        user_history[user_id].add(final_word)
        bot.send_message(message.chat.id, f"@{final_word}")
        return

    # Выдача из баз
    if cat in categories and categories[cat]:
        final_word = None
        for _ in range(150):
            word = random.choice(categories[cat])

            # Если это слова, проверяем орфографию
            if cat in ['final', 'semi']:
                if word in spell and word not in user_history[user_id]:
                    final_word = word
                    break
            # Для остальных просто проверяем уникальность
            else:
                if word not in user_history[user_id]:
                    final_word = word
                    break

        if not final_word:
            final_word = random.choice(categories[cat])

        user_history[user_id].add(final_word)
        bot.send_message(message.chat.id, f"@{final_word}")
    else:
        bot.send_message(message.chat.id, "База пуста или не загрузилась.")

if __name__ == '__main__':
    load_data()
    print("Бот готов!")
    bot.infinity_polling()
