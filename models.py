import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    token = Column(Text, default="")


class Movie(Base):
    __tablename__ = "movies"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    genre = Column(String, default="")
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    uploaded_by = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    comments = relationship(
        "Comment",
        back_populates="movie",
        cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True, default=gen_uuid)
    movie_id = Column(String, ForeignKey("movies.id"), nullable=False)
    username = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    movie = relationship("Movie", back_populates="comments")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)  # "system" | "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)