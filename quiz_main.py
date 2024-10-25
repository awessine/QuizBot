import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from quiz_db import create_table, get_list_of_questions, get_question, get_quiz_index, get_result, get_top_users, save_result, update_quiz_index

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Замените "YOUR_BOT_TOKEN" на токен, который вы получили от BotFather
API_TOKEN = '8070025104:AAEcvqdwyyAUMi93Qp-10Wv85_Pz0LRtidI'
# Читаем список вопросов из json файла
quiz_data = get_list_of_questions('quiz_data.json')

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем сборщика клавиатур типа Reply
    builder = ReplyKeyboardBuilder()
    # Добавляем в сборщик одну кнопку
    builder.add(types.KeyboardButton(text="Начать игру"))
    builder.add(types.KeyboardButton(text="Лучшие результаты"))
    # Прикрепляем кнопки к сообщению
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

# Хэндлер на команду /quiz
@dp.message(Command("quiz"))
@dp.message(F.text=="Начать игру")
async def cmd_quiz(message: types.Message):
    # Логика начала квиза
     # Отправляем новое сообщение без кнопок
    await message.answer(f"Давайте начнем квиз!")
    # Запускаем новый квиз
    await new_quiz(message)

@dp.message(Command("top_results"))
@dp.message(F.text=="Лучшие результаты")
async def cmd_top_results(message: types.Message):
    top_users = await get_top_users()
    
    if top_users:
        response = "Топ 5 пользователей с наибольшим результатом:\n"
        for user_id, result in top_users:
            user_info = await bot.get_chat(user_id)
            response += f"Пользователь : @{user_info.username if user_info.username else "Не указан"}, Результат: {result}\n"
        await message.answer(response)
    else:
        await message.answer("Нет доступных результатов.")

async def reply_on_answer(callback):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    button_text = callback.data.split('|')[0] 
    await callback.message.answer(f"\U0001F4E8 Ваш ответ: {button_text}")

async def check_for_end(current_question_index, callback):
    if current_question_index < len(quiz_data):
        # Следующий вопрос
        await get_question(callback.message, callback.from_user.id)
    else:
        # Уведомление об окончании квиза
        result = await get_result(callback.from_user.id)
        await callback.message.answer(f"Это был последний вопрос. Квиз завершен!\nВаш результат: {result} верных ответа")


@dp.callback_query(F.data.split('|')[1] == "right_answer")
async def right_answer(callback: types.CallbackQuery):
    # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await reply_on_answer(callback)

    # Получение текущего вопроса для данного пользователя
    current_question_index = await get_quiz_index(callback.from_user.id)

    # Отправляем в чат сообщение, что ответ верный
    await callback.message.answer("\U00002705 Верно!")

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    #Сохраняем результат
    result = await get_result(callback.from_user.id)
    result += 1
    await save_result(result, callback.from_user.id)
    # Проверяем достигнут ли конец квиза
    await check_for_end(current_question_index, callback)
        
@dp.callback_query(F.data.split('|')[1] == "wrong_answer")
async def wrong_answer(callback: types.CallbackQuery):
    # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await reply_on_answer(callback)

    # Получение текущего вопроса для данного пользователя
    current_question_index = await get_quiz_index(callback.from_user.id)

    correct_option = quiz_data[current_question_index]['correct_option']

    # Отправляем в чат сообщение об ошибке с указанием верного ответа
    await callback.message.answer(f"\U0000274C Неверно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    # Проверяем достигнут ли конец квиза
    await check_for_end(current_question_index, callback)

async def new_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    # сбрасываем значение текущего индекса вопроса квиза в 0
    current_question_index = 0
    await update_quiz_index(user_id, current_question_index)
    result = 0
    await save_result(result, user_id)
    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id)

# Запуск процесса поллинга новых апдейтов
async def main():
    await create_table()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())