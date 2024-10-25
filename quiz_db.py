import aiosqlite
import json
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

def get_list_of_questions(file_path):
   with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)   

quiz_data = get_list_of_questions('quiz_data.json')
DB_NAME = 'quiz_bot.db'

async def create_table():
    # Создаем соединение с базой данных (если она не существует, то она будет создана)
    async with aiosqlite.connect('quiz_bot.db') as db:
        # Выполняем SQL-запрос к базе данных
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER, result INTEGER)''')
        # Сохраняем изменения
        await db.commit()

def generate_options_keyboard(answer_options, right_answer):
  # Создаем сборщика клавиатур типа Inline
    builder = InlineKeyboardBuilder()

    # В цикле создаем 4 Inline кнопки, а точнее Callback-кнопки
    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            # Текст на кнопках соответствует вариантам ответов
            text=option,
            # Присваиваем данные для колбэк запроса.
            # Если ответ верный сформируется колбэк-запрос с данными 'right_answer'
            # Если ответ неверный сформируется колбэк-запрос с данными 'wrong_answer'
            callback_data = option + "|right_answer" if option == right_answer else option + "|wrong_answer")
        )

    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()

# Запускаем создание таблицы базы данных
async def update_quiz_index(user_id, index):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        result = await get_result(user_id)
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, result) VALUES (?, ?, ?)', (user_id, index, result))
        # Сохраняем изменения
        await db.commit()

async def get_quiz_index(user_id):
     # Подключаемся к базе данных
     async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0

async def get_question(message, user_id):

    # Запрашиваем из базы текущий индекс для вопроса
    current_question_index = await get_quiz_index(user_id)
    # Получаем индекс правильного ответа для текущего вопроса
    correct_index = quiz_data[current_question_index]['correct_option']
    # Получаем список вариантов ответа для текущего вопроса
    opts = quiz_data[current_question_index]['options']

    # Функция генерации кнопок для текущего вопроса квиза
    # В качестве аргументов передаем варианты ответов и значение правильного ответа (не индекс!)
    kb = generate_options_keyboard(opts, opts[correct_index])
    # Отправляем в чат сообщение с вопросом, прикрепляем сгенерированные кнопки
    await message.answer(f"\U00002753 {quiz_data[current_question_index]['question']}", reply_markup=kb)

async def save_result(result, user_id):
     async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        index = await get_quiz_index(user_id)
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, result) VALUES (?, ?, ?)', (user_id, index, result))
        # Сохраняем изменения
        await db.commit()

async def get_result(user_id):
     async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        async with db.execute('SELECT result FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0
            
async def get_top_users(limit=5):
    async with aiosqlite.connect(DB_NAME) as db:
        # Запрашиваем 5 пользователей с самым большим результатом
        async with db.execute('SELECT user_id, result FROM quiz_state ORDER BY result DESC LIMIT ?', (limit,)) as cursor:
            results = await cursor.fetchall()
            return results
