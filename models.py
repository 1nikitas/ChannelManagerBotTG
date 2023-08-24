from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from sqlalchemy import Column, Integer, String


class Bots(Base):
    __tablename__ = 'bots'

    id = Column(Integer, primary_key=True, autoincrement=True)  # New auto-incrementing ID column
    owner_id = Column(Integer)
    bot_name = Column(String)
    bot_token = Column(String)
    admins = Column(String)


class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    channel = Column(String)
    post = Column(String)
    reactions = Column(String)
    hidden_continuation = Column(String)
    sound = Column(String)
    comments = Column(String)
    pin = Column(String)
    copy_ = Column(String, name="copy")
    share = Column(String)
    response = Column(String)
    buttons = Column(String)
    medias = relationship("PostMedia", back_populates="post", cascade="all, delete")


class AdminChannel(Base):
    __tablename__ = 'admin_channels'
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer)
    channel_id = Column(Integer)
    channel_name = Column(String)
    channel_username = Column(String)
    bot_id = Column(Integer)


class UserBot(Base):
    __tablename__ = 'UserBots'
    user_id = Column(Integer, primary_key=True)
    bot_name = Column(String)


class PostMedia(Base):
    __tablename__ = 'post_medias'
    post_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    media_id = Column(String, primary_key=True)
    post = relationship("Post", back_populates="medias")


class Reaction(Base):
    __tablename__ = 'reactions'
    id = Column(Integer, primary_key=True)
    custom_emoji_id = Column(String)  # Идентификатор кастомного эмодзи
    post_id = Column(Integer, ForeignKey('posts.id'))