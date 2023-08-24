import asyncio
import json
import logging
import re
from contextlib import contextmanager

import aiogram
from aiogram import Bot, Dispatcher
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import WebAppInfo, CallbackQuery
from aiogram.utils.exceptions import BadRequest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import session, joinedload
from aiogram.utils import exceptions

from models import AdminChannel, Bots, PostMedia, Reaction
from models import Base, Post
from server import SessionLocal
from tg_api_requests import get_bot_info, check_token_validity

API_TOKEN = '1157522702:AAHvkKHzvlZv6O-Cs7MHre0EiZ0hG2GIZjE'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker





DATABASE_URL = "sqlite:///./bots.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

@contextmanager
def create_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


dispatchers = {}


class BotUpdateToken(StatesGroup):
    waiting_for_new_token = State()

class Form(StatesGroup):
    Channel = State()
    Post = State()

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)


class ReactionState(StatesGroup):
    reactions = State()


async def start_bot(token):
    bot = Bot(token=token)
    dp = Dispatcher(bot, storage=MemoryStorage())

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    def get_post_settings(post_id: str) -> dict:
        session = SessionLocal()  # создание новой сессии
        try:
            post = session.query(Post).filter_by(id=post_id).first()
            if not post:
                logging.error(f"No post found with ID {post_id}.")
                return {}

            settings_map = {
                'channel': post.channel,
                "post": post.post,
                "medias": "Медиа",
                "reactions": "Реакции",
                "hidden_continuation": "Продолжение",
                "sound": "Звук",
                "comments": "Комментарии",
                "pin": "Закрепить",
                "copy_": "Копировать",
                "share": "Поделиться",
                "response": "Ответ",
                "buttons": "Кнопки"
            }

            settings = {}
            for setting in settings_map.keys():
                settings[setting] = getattr(post, setting)

            return settings
        finally:
            session.close()  # закрытие сессии после выполнения операций

    def get_medias_for_post(session, post_id):
        post = session.query(Post).filter_by(id=post_id).first()
        if post:
            return [media.media_id for media in post.medias]
        return []

    def get_channel_name(cursor, post_id):
        result = cursor.fetchone()
        if result:
            return result[0]
        return None

    def get_channel_id(session, channel_name):
        channel = session.query(AdminChannel).filter_by(channel_name=channel_name).first()
        return channel.channel_id if channel else None

    # async def send_post_to_channel(post_id, channel_id):
    #     # Fetch the post content from the database
    #     result = cursor.fetchone()
    #
    #     if result:
    #         post_content = result[0]
    #         try:
    #             await bot.send_message(chat_id=channel_id, text=post_content)
    #             print(f"Sent post to channel {channel_id}")
    #         except Exception as e:
    #             print(f"Error sending post to channel: {e}")
    #     else:
    #         print("Post not found for the given post ID.")


    def parse_buttons_string(buttons_string):
        try:
            # Попытка десериализовать строку JSON в список словарей
            buttons_data = json.loads(buttons_string)
            logging.error(f"[!]buttons_data: {buttons_data}")
            return buttons_data
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON: {e}")
            return []

    def create_keyboard_from_buttons(buttons_data):
        keyboard = InlineKeyboardMarkup()
        if not buttons_data:
            return
        for row_data in buttons_data:
            row = []
            for button_data in row_data:
                button = InlineKeyboardButton(text=button_data['name'], url=button_data['url'])
                row.append(button)
            keyboard.row(*row)
        return keyboard

    def get_post_by_id(post_id):
        session = SessionLocal()
        try:
            post = session.query(Post).filter_by(id=post_id).first()
            return post
        except Exception as e:
            print(f"Error retrieving post by ID: {e}")
            return None
        finally:
            session.close()

    async def handle_buttons(call, buttons):
        markup = types.InlineKeyboardMarkup()
        for button_text in buttons:
            button = types.InlineKeyboardButton(text=button_text, callback_data=f"action_{button_text}")
            markup.add(button)
        await bot.send_message(chat_id=call.from_user.id, text="Choose an action:", reply_markup=markup)

    def settings_keyboard(post: Post) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup(row_width=2)

        settings_map = {
            "medias": "Медиа",
            "reactions": "Реакции",
            "hidden_continuation": "Продолжение",
            "sound": "Без звука",
            "comments": "Комментарии",
            "pin": "Закрепить",
            "copy_": "Копировать",
            "share": "Поделиться",
            "response": "Ответ",
            "buttons": "Кнопки"
        }

        buttons = []

        for setting, label in settings_map.items():
            value = getattr(post, setting)
            print(f"Setting: {setting}, Value: {value}")  # Добавьте эту строку для дебага

            if value == '0' or value is False:  # Изменено условие
                buttons.append(InlineKeyboardButton(text=f"{label} ❌", callback_data=f"toggle_{setting}_{post.id}"))
            else:
                buttons.append(InlineKeyboardButton(text=f"{label} ✅", callback_data=f"toggle_{setting}_{post.id}"))

        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                markup.add(buttons[i], buttons[i + 1])
            else:
                markup.add(buttons[i])

        markup.row(InlineKeyboardButton(text="Опубликовать", callback_data=f"publish_{post.id}"))
        markup.row(InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{post.id}"))
        print(markup)
        return markup


    async def send_to_channel(s, bot, post: Post, channel_id, reply_to_message_id=None):
        medias = get_medias_for_post(session=s, post_id=post.id) if post.medias else None
        sound = not post.sound
        buttons_str = post.buttons
        buttons_data = parse_buttons_string(buttons_str) if buttons_str else None
        keyboard = create_keyboard_from_buttons(buttons_data) if buttons_data else None

        if len(medias) == 1:  # Одно фото
            return await bot.send_photo(
                chat_id=channel_id,
                photo=medias[0],  # Используем напрямую
                caption=post.post,
                disable_notification=sound,
                reply_markup=keyboard,
                protect_content=post.copy_,
                reply_to_message_id=reply_to_message_id  # Добавьте этот параметр

            )
        elif medias:
            media_group = [types.InputMediaPhoto(media=media_id) for media_id in medias]
            media_group[0].caption = post.post  # Добавляем текст к первой картинке
            await bot.send_media_group(
                chat_id=channel_id,
                media=media_group,
                disable_notification=sound,
                protect_content=post.copy_
            )
            return None
        else:
            return await bot.send_message(
                chat_id=channel_id,
                text=post.post,
                disable_notification=sound,
                disable_web_page_preview=post.hidden_continuation,
                reply_markup=keyboard,
                protect_content=post.copy_,
                reply_to_message_id=reply_to_message_id,
            )

    async def handle_post_response(s, bot, post: Post):
        if not post.response:
            return

        parts = post.response.split('/')
        if len(parts) != 5:
            await bot.send_message(post.user_id, "Некорректный формат ссылки.")
            return

        channel_username = parts[-2]
        message_id = int(parts[-1])
        admin_channel = s.query(AdminChannel).filter_by(channel_username=channel_username).first()
        if not admin_channel:
            await bot.send_message(post.user_id, "Канал не найден в базе данных.")
            return

        await send_to_channel(s, bot, post, admin_channel.channel_id, message_id)

    @dp.callback_query_handler(lambda c: c.data.startswith('reject_'))
    async def reject_post(call: types.CallbackQuery):
        post_id = int(call.data.split('_')[1])

        with create_session() as s:
            post = s.query(Post).filter_by(id=post_id).first()
            if post:
                s.delete(post)
                s.commit()

        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await bot.answer_callback_query(call.id, "Пост отклонен и удален.")

    @dp.callback_query_handler(lambda c: c.data.startswith('publish_'))
    async def publish_post(call: types.CallbackQuery):
        post_id: str = call.data.split('_')[-1]
        with create_session() as s:
            post = s.query(Post).filter_by(id=post_id).first()
            if not post:
                logging.error(f"No post found with ID {post_id}.")
                return

            channel_name = post.channel
            channel_id = get_channel_id(s, channel_name) if channel_name else None
            if not channel_id:
                logging.error("Channel ID not found for the given post ID.")
                return

            sent_message = await send_to_channel(s, bot, post, channel_id)
            if sent_message and post.pin != '0':
                await bot.pin_chat_message(chat_id=channel_id, message_id=sent_message.message_id)
            await handle_post_response(s, bot, post)

        await bot.send_message(call.from_user.id, "Пост опубликован!")

    ####
    def update_setting_in_db(post_id: int, setting: str, value: int):
        with create_session() as s:
            try:
                s.query(Post).filter_by(id=post_id).update({setting: value})
                s.commit()

            except SQLAlchemyError as e:
                s.rollback()
                raise e


    @dp.callback_query_handler(lambda c: "reactions" in c.data)
    async def process_toggle_setting(callback_query: CallbackQuery, ):
        await callback_query.message.answer("Теперь введи разрешенные реакции через запятую:")
        await ReactionState.reactions.set()

    @dp.message_handler(state=ReactionState.reactions)
    async def set_text(message: types.Message, state: FSMContext):
        with create_session() as s:
            post = s.query(Post).filter(Post.user_id == message.from_user.id).first()

            async with state.proxy() as data:
                custom_emoji_ids = [
                    message.entities[i].custom_emoji_id for i in range(len(message.entities)) if message.entities
                ]

                if not custom_emoji_ids:
                    return

                post.reactions = 1
                s.commit()

                for custom_emoji_id in custom_emoji_ids:

                    new_reaction = Reaction(custom_emoji_id=custom_emoji_id, post_id=post.id)  # Use post.id here
                    s.add(new_reaction)
                    s.commit()

            await message.answer('Реакции сохранены!')
            await send_post_message(s, bot, post)

        await state.finish()

    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('toggle_'))
    async def process_toggle_setting(callback_query: CallbackQuery, state: FSMContext):
        logging.info(f"Полученные данные: {callback_query.data}")
        _, setting, post_id = callback_query.data.split('_', maxsplit=2)

        with create_session() as s:
            post = s.query(Post).options(joinedload('medias')).filter_by(id=post_id).first()

            if not post:
                logging.error(f"No post found with ID {post_id}.")
                return

            logging.error(f"Получен параметр: {getattr(post, setting)}")

            if getattr(post, setting) == '1':
                new_value = 0
                logging.error(f"!!!!!Получен параметр: {getattr(post, setting)}")
            else:
                new_value = 1

            # Update the setting in the database
            setattr(post, setting, str(new_value))
            s.commit()

            # Get the updated markup
            updated_markup = settings_keyboard(post)

            try:
                await callback_query.message.edit_reply_markup(reply_markup=updated_markup)
            except exceptions.MessageNotModified:
                pass

        await callback_query.answer()

    @dp.message_handler(commands=['start'])
    async def send_welcome(message: types.Message):
        await message.answer("Добро пожаловать! Чтобы начать:\n\n"
                             "1. Добавьте бота в администраторы канала.\n"
                             "2. Переслать любое сообщение из канала в чат с ботом.")

    async def send_post_message(s, bot, post):
        # Определите логику отправки сообщения на основе параметров в объекте Post
        text = f"Ваши текущие настройки:"

        post_text = post.post if post.post else 'Пустой текст'
        media_items = post.medias

        # Создаем список медиа-элементов для отправки в виде media_group
        media_group = []
        for index, media_item in enumerate(media_items):
            if index == 0:
                # Добавляем текст (caption) к первому изображению
                media_group.append(types.InputMediaPhoto(media=media_item.media_id, caption=post_text))
            else:
                media_group.append(types.InputMediaPhoto(media=media_item.media_id))

        # Опционально, добавьте кнопки в клавиатуру, если есть
        if post.buttons:
            buttons_data = parse_buttons_string(post.buttons)
            keyboard = create_keyboard_from_buttons(buttons_data)
        else:
            keyboard = None

        # Отправляем текстовое сообщение
        await bot.send_message(
            chat_id=post.user_id,
            text=text,
            reply_markup=keyboard,
        )

        if post.medias:
            await bot.send_media_group(
                chat_id=post.user_id,
                media=media_group,
            )

        await bot.send_message(
            chat_id=post.user_id,
            text=text,
            reply_markup=settings_keyboard(post),
        )


    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('finish_'))
    async def process_finish_callback(callback_query: CallbackQuery):
        logging.info("process_finish_callback triggered")
        post_id = callback_query.data.split('_')[1]

        with create_session() as s:
            post = s.query(Post).filter_by(id=post_id).first()

            if not post:
                logging.error(f"No post found with ID {post_id}.")
                return

            logging.info(f"Found post with ID {post_id}.")

            await send_post_message(s, bot, post)

        # except Exception as e:
        #     logging.error(f"Error sending post with media: {e}")

    @dp.message_handler(content_types=['photo', 'video', 'document'])
    async def handle_media(message: types.Message):
        media_id = message.photo[-1].file_id if message.photo else None
        session = SessionLocal()

        if media_id:
            logging.info(f"Received media with ID: {media_id}")

            # Download the file
            try:
                file_path = await bot.get_file(file_id=media_id)
                download_path = f"media/{media_id}.jpg"  # You can adjust the file path as needed
                await bot.download_file(file_path.file_path, destination=download_path)
                logging.info(f"Saved media with ID {media_id} to {download_path}")
            except Exception as e:
                logging.error(f"Error downloading and saving the file: {e}")

            # Поиск поста по user_id
            user_id = message.from_user.id

            try:
                # Если состояние 'collecting_media', сохраняем медиа в базу данных
                post = session.query(Post).filter_by(user_id=user_id).order_by(Post.id.desc()).first()
                if post:
                    post_media = PostMedia(media_id=media_id, post=post)
                    session.add(post_media)
                    session.commit()
                    logging.info(f"Added media with ID {media_id} to the post with ID {post.id}.")
                else:
                    logging.warning(f"No post found for user {user_id} to attach media.")
            except Exception as e:
                logging.error(f"Error saving media to database: {e}")
        else:
            logging.warning("Received media outside of the collecting_media state.")

    @dp.callback_query_handler(lambda c: c.data.startswith('yes_'))
    async def query_yes(call: types.CallbackQuery):
        logging.info("Handling 'yes_' callback")
        post_id = call.data.split('_')[1]
        print(f'post_id: {post_id}')
        markup = types.InlineKeyboardMarkup()
        finish_button = types.InlineKeyboardButton("Завершить", callback_data=f'finish_{post_id}')
        markup.add(finish_button)
        await bot.send_message(call.from_user.id,
                               "Пришлите медиа, которое вы хотите прикрепить. Когда закончите, нажмите 'Завершить'",
                               reply_markup=markup)
        await call.answer()
        logging.info("'yes_' callback handled successfully")


    @dp.callback_query_handler(lambda c: c.data.startswith('no_'))
    async def query_yes(call: types.CallbackQuery):
        await process_finish_callback(callback_query=call)


    @dp.callback_query_handler(lambda c: c.data == 'publish')
    async def publish_post(call: types.CallbackQuery):
        # Здесь вы можете опубликовать пост в вашем канале или группе.
        # Для примера просто отправим ответное сообщение пользователю.
        await bot.send_message(call.from_user.id, "Пост опубликован!")

    @dp.callback_query_handler(lambda c: c.data == 'reject')
    async def reject_post(call: types.CallbackQuery):
        # Здесь вы можете сделать любые действия, связанные с отклонением поста.
        await bot.send_message(call.from_user.id, "Пост отклонен!")

    @dp.message_handler(content_types=types.ContentType.ANY)
    async def register_channel(message: types.Message):
        print(message.content_type)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        user_id = message.from_user.id
        await message.answer(f'https://8c0e-212-45-15-105.ngrok-free.app/?user_id={message.from_user.id}')
        button = types.KeyboardButton('Создать пост', web_app=WebAppInfo(
            url=f'https://8c0e-212-45-15-105.ngrok-free.app/?user_id={message.from_user.id}'))
        keyboard.add(button)

        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
            channel_name = message.forward_from_chat.title
            channel_username = message.forward_from_chat.username
            print(f'linked_chat_id: {message.forward_from_chat.linked_chat_id}')
            try:
                await bot.get_chat_member(channel_id, bot.id)
            except Exception as e:
                await message.answer(f"Бот не является администратором канала.")
            else:
                with create_session() as s:
                    # Вставка данных в таблицу admin_channels
                    s.add(AdminChannel(channel_id=channel_id, channel_name=channel_name, bot_id=bot.id,
                                       admin_id=message.from_user.id, channel_username=channel_username))
                    s.commit()
                await message.answer("Канал зарегистрирован и готов к использованию.", reply_markup=keyboard)
        else:
            await message.answer("Пожалуйста, перешлите сообщение из канала, чтобы зарегистрировать его.")
    # Start the bot
    await dp.start_polling()


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Регистрация нового бота", "Управление ботами"]
    keyboard.add(*buttons)
    await message.answer("Приветствую вас! Вы можете зарегистрировать нового бота", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Регистрация нового бота")
async def cmd_register(message: types.Message):
    await message.answer(
        "Бот для постинга создается в 2 этапа:\n"
        "1. Создайте основу для бота в @BotFather:\n"
        "- Запустите @BotFather и отправьте ему команду /newbot\n"
        "- Придумайте и отправьте имя для бота\n"
        "- Придумайте и отправьте логин для бота\n"
        "Важно! Логин для бота должен быть уникальным и заканчиваться на bot\n"
        "2. После успешной регистрации отправьте в этот чат полученное сообщение от @BotFather"
    )


@dp.message_handler(lambda message: message.text == "Управление ботами")
async def cmd_manage(message: types.Message):
    user_id = message.from_user.id

    with create_session() as s:  # используем контекстный менеджер, который мы определили ранее
        bots = s.query(Bots.bot_name).filter(Bots.owner_id == user_id).all()
        bot_names = [f'@{bot_name[0]}' for bot_name in bots]

    if not bot_names:
        await message.answer(
            "Зарегистрированные боты отсутствуют. Для управления ботами создайте хотя бы одного",
            reply_markup=types.ReplyKeyboardMarkup(
                resize_keyboard=True, one_time_keyboard=True
            ).add("Регистрация нового бота")
        )
    else:
        await message.answer(
            "Выберите в списке необходимого бота",
            reply_markup=types.ReplyKeyboardMarkup(
                resize_keyboard=True
            ).add(*bot_names)
        )


@dp.message_handler(lambda message: message.text == "Проверить Токен")
async def handle_check_token(message: types.Message):
    user_id = message.from_user.id

    with create_session() as s:
        bot_token_obj = s.query(Bots.bot_token).filter(Bot.owner_id == user_id).first()
        if not bot_token_obj:
            await message.answer("Токен не найден")
            return
        bot_token = bot_token_obj[0]

    is_valid = check_token_validity(bot_token)  # assuming the function check_token_validity validates the token
    if is_valid:
        await message.answer("Проверка успешна")
    else:
        await message.answer("Токен недействителен, пожалуйста обновите данные",
                             reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Обновить Токен"))


@dp.message_handler(lambda message: message.text == "Обновить Токен")
async def handle_update_token(message: types.Message):
    await message.answer("Отправьте сообщение с полученным токеном из @BotFather")


@dp.message_handler(regexp=r'^\d+:[a-zA-Z0-9_-]+$')
async def register_bot(message: types.Message):
    token_message = message.text
    bot_username = await get_bot_info(token_message)

    user_id = message.from_user.id

    with create_session() as s:
        new_bot = Bots(owner_id=user_id, bot_name=bot_username, bot_token=token_message)
        s.add(new_bot)
        s.commit()

    await message.answer(f"Поздравляем! Регистрация бота @{bot_username} прошла успешно. "
                         f"Чтобы начать работать зайдите в него и отправьте команду /start, "
                         f"если не делали этого раньше, и завершите настройку.")
    await start_bot(token_message)


@dp.message_handler()
async def bot_selected(message: types.Message):
    bot_name_requested = message.text.lstrip('@')  # remove '@' if present

    with create_session() as s:
        bot_data = s.query(Bots).filter(Bots.bot_name == bot_name_requested).first()

    if bot_data:
        markup = types.InlineKeyboardMarkup(row_width=2)
        item1 = types.InlineKeyboardButton("Настроить", url=f't.me/{bot_data.bot_name}')
        item2 = types.InlineKeyboardButton("Проверить Токен", callback_data=f'check_token:{bot_data.id}')
        item3 = types.InlineKeyboardButton("Обновить Токен", callback_data=f'update_token:{bot_data.id}')
        item6 = types.InlineKeyboardButton("Управление правами", callback_data=f'rights_management:{bot_data.id}')
        item7 = types.InlineKeyboardButton("Удалить Бота", callback_data=f'delete_bot:{bot_data.id}')
        item8 = types.InlineKeyboardButton("Назад", callback_data=f'go_back:{bot_data.id}')
        markup.add(item1, item2, item3, item6, item7, item8)

        await message.answer(text="Выберите действие:", reply_markup=markup)
    else:
        await message.answer(text="Бот не найден. Попробуйте снова.")


@dp.callback_query_handler(lambda c: c.data.startswith('rights_management'))
async def process_callback_rights_management(callback_query: types.CallbackQuery):
    _, bot_id = callback_query.data.split(':')
    bot_id = int(bot_id)

    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("Добавить Администратора", callback_data=f'add_admin:{bot_id}')
    item2 = types.InlineKeyboardButton("Удалить Администратора", callback_data=f'remove_admin:{bot_id}')
    item3 = types.InlineKeyboardButton("Передать Бота", callback_data=f'transfer_bot:{bot_id}')
    item4 = types.InlineKeyboardButton("Назад", callback_data=f'go_back')
    markup.add(item1, item2, item3, item4)

    await bot.send_message(callback_query.from_user.id, "Выберите действие:", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('go_back'))
async def process_callback_check_token(callback_query: types.CallbackQuery):
    await cmd_start(message=callback_query.message)


@dp.callback_query_handler(lambda c: c.data.startswith('check_token'))
async def process_callback_check_token(callback_query: types.CallbackQuery):
    _, bot_id = callback_query.data.split(':')
    bot_id = int(bot_id)

    with create_session() as s:
        bot_data = s.query(Bot).filter(Bots.id == bot_id).first()

    if not bot_data:
        await callback_query.answer(text="Бот не найден")
        return

    valid = await check_token_validity(bot_data.bot_token)

    if valid:
        await callback_query.answer(text="Токен актуален")
    else:
        await callback_query.answer(text="Токен не актуален")


@dp.callback_query_handler(lambda c: c.data.startswith('update_token'))
async def process_callback_update_token(callback_query: types.CallbackQuery):
    _, bot_id = callback_query.data.split(':')
    bot_id = int(bot_id)

    await bot.send_message(callback_query.from_user.id, "Пожалуйста, отправьте новый токен.")

    await BotUpdateToken.next()


@dp.message_handler(state=BotUpdateToken.waiting_for_new_token)
async def process_new_token(message: types.Message, state: FSMContext):
    new_token = message.text
    user_id = message.from_user.id

    # Validate the new token and update it in the database
    match = re.match(r'^\d+:[a-zA-Z0-9_-]+$', new_token)
    valid = await check_token_validity(new_token)
    if match and valid:

        await message.answer("Токен обновлен успешно.")
    else:
        await message.answer("Возникли проблемы с обновлением токена, проверьте корректность сообщения.")

    await state.finish()


async def main():
    tasks = [asyncio.create_task(dp.start_polling())]

    with create_session() as s:
        tokens = s.query(Bots.bot_token).all()

    for token_tuple in tokens:
        token = token_tuple[0]
        tasks.append(asyncio.create_task(start_bot(token)))

    await asyncio.gather(*tasks)



if __name__ == '__main__':
    asyncio.run(main())