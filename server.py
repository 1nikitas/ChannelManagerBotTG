import sqlite3
from pathlib import Path

import aiofiles as aiofiles
from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException, Query, Depends
from typing import List, Union, Optional

from sqlalchemy import Column, Integer, String, Boolean, Text, create_engine, ForeignKey, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, relationship, session, Session
from sqlalchemy.ext.declarative import declarative_base

from pydantic import BaseModel
from starlette.responses import JSONResponse

from models import AdminChannel, Bots, Base, Post

app = FastAPI()
templates = Jinja2Templates(directory="templates")

engine = create_engine('sqlite:///./bots.db')
SessionLocal = sessionmaker(bind=engine)  # Создаем фабрику сессий

# Вместо создания таблиц с помощью sqlite3 используйте Base.metadata.create_all(bind=engine)
Base.metadata.create_all(bind=engine)


class Channel(BaseModel):
    id: int
    admin_id: int
    channel_id: int
    channel_name: str
    bot_id: int



@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "create_post_.html", {
            "request": request
        }
    )




@app.get("/test", response_class=HTMLResponse)
async def root(request: Request):
    API_TOKEN = '6014701692:AAFlZ3YXT7cOpszl9gdH95q206_FAcZiI2M'

    bot = Bot(token=API_TOKEN)
    await bot.send_message(chat_id='-1001904800700', text="1111")
    """-1001904800700"""
    return JSONResponse(status_code=200, content={})


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from pydantic import BaseModel


class PostData(BaseModel):
    channel: str
    post: Optional[str]
    media: Optional[List[str]] = []
    reactions: Optional[Union[bool, str]] = False
    hidden_continuation: Optional[bool] = False
    sound: Optional[bool] = False
    comments: Optional[bool] = False
    pin: Optional[bool] = False
    copy_: Optional[bool] = False
    share: Optional[bool] = False
    response: Optional[Union[bool, str]] = False
    buttons: Optional[Union[bool, str]] = False


@app.post("/submit_post/")
async def submit_post(data: PostData, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        print(data.__dict__)
        post = Post(
            user_id=user_id,
            channel=data.channel,
            post=data.post,
            reactions=True if data.reactions else False,
            hidden_continuation=True if data.hidden_continuation == 'True' else False,
            sound=True if data.sound == True else False,
            comments=True if data.comments == True else False,
            pin=True if data.pin == True else False,
            copy_=True if data.copy_== True else False,
            share=True if data.share == True else False,
            response=data.response if data.response else False,
            buttons=str(data.buttons).strip() if data.buttons else False
        )
        db.add(post)
        db.commit()

        print(f"user_id: {post.user_id}")
        print(f"channel: {post.channel}")
        print(f"post: {post.post}")
        print(f"reactions: {post.reactions}")
        print(f"hidden_continuation: {post.hidden_continuation}")
        print(f"sound: {post.sound}")
        print(f"comments: {post.comments}")
        print(f"pin: {post.pin}")
        print(f"copy_: {post.copy_}")
        print(f"share: {post.share}")
        print(f"response: {post.response}")
        print(f"buttons: {post.buttons}")

        post_id = post.id

        result = db.query(Bots.bot_token).filter(Bots.owner_id == user_id).first()

        if result is None:
            raise HTTPException(status_code=404, detail="Bot not found")

        bot_token = result[0]
        bot = Bot(token=bot_token)

        markup = types.InlineKeyboardMarkup(row_width=2)
        item1 = types.InlineKeyboardButton("Да", callback_data=f'yes_{post_id}')
        item2 = types.InlineKeyboardButton("Нет", callback_data=f'no_{post_id}')
        markup.row(item1, item2)

        await bot.send_message(chat_id=user_id, text="Хотите ли вы прикрепить медиа?", reply_markup=markup)

        return {"message": "Пост успешно зарегистрирован"}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()



@app.post("/upload_media/")
async def upload_media(media: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    media_filenames = []

    # Query the last post id
    last_post = db.query(Post).order_by(desc(Post.id)).first()
    last_post_id = last_post.id if last_post else None

    print(f'last_post_id: {last_post_id}')
    # If there is no post in the database, last_post_id will be None

    # Save media files and collect their paths
    for file in media:
        try:
            # Save file
            filepath = f"media/{file.filename}"
            async with aiofiles.open(filepath, 'wb') as out_file:
                content = await file.read()  # async read
                await out_file.write(content)  # async write

            # Collect filename
            media_filenames.append(filepath)

        except Exception as e:
            raise HTTPException(status_code=500, detail="An error occurred while saving the media file.")

    return JSONResponse(status_code=200, content={"media_filenames": media_filenames, "last_post_id": last_post_id})


@app.get("/channels/{admin_id}")
async def get_channels_by_admin(admin_id: int, db: Session = Depends(get_db)):
    channels = db.query(AdminChannel.channel_name).filter(AdminChannel.admin_id == admin_id).all()
    if not channels:
        raise HTTPException(status_code=404, detail="Channels not found")
    return [channel[0] for channel in channels]


