from sqlalchemy import Column, Integer, String, Float, ARRAY, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    isbn = Column(String, unique=True, index=True)
    description = Column(String)
    subjects = Column(ARRAY(String))
    rating = Column(Float)
    # Optional: add vector = Column(ARRAY(Float)) if still needed for FAISS

    user_books = relationship("UserBook", back_populates="book")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_books = relationship("UserBook", back_populates="user")

class UserBook(Base):
    __tablename__ = "user_books"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id"), primary_key=True)
    rating = Column(Float)
    user = relationship("User", back_populates="user_books")
    book = relationship("Book", back_populates="user_books")
    __table_args__ = (UniqueConstraint('user_id', 'book_id', name='_user_book_uc'),)
