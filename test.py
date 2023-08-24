from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

# Создаем объект бота и диспетчера
bot = Bot(token="5894771541:AAEWNBb_ANfYlzz4yWUBQA8zx1BpqrbpcmY")
dp = Dispatcher(bot)

# Определите список разрешенных реакций (кастомных эмодзи)
allowed_reactions = ["👍", "❤️"]

@dp.message_handler()
async def handle_message(message: types.Message):
    print(message)





if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
