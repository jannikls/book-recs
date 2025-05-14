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

    vector = Column(ARRAY(Float))  # Added for FAISS vector search

    cover_url = Column(String)  # URL to cover image



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

    shelf = Column(String, default="to-read")

    review = Column(String)

    notes = Column(String)

    date_added = Column(String)

    user = relationship("User", back_populates="user_books")

    book = relationship("Book", back_populates="user_books")

    __table_args__ = (UniqueConstraint('user_id', 'book_id', name='_user_book_uc'),)



class Cluster(Base):

    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False, unique=True)



class ClusterBook(Base):

    __tablename__ = "cluster_books"

    id = Column(Integer, primary_key=True, index=True)

    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)

    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    read_count = Column(Integer, default=0)

    cluster_niche_score = Column(Float, default=0.0)

    cluster = relationship("Cluster")

    book = relationship("Book")

# --- Scaffold: ReadingList model for API/UI development only ---

class PhotoCapture(Base):
    __tablename__ = "photo_captures"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_path = Column(String)
    uploaded_at = Column(String)  # Use String for demo; change to DateTime if DB is migrated
    ocr_text = Column(String)
    type = Column(String)  # "cover" or "page"

class PhotoBookMatch(Base):
    __tablename__ = "photo_book_matches"
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photo_captures.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    match_score = Column(Float)

class ReadingList(Base):
    __tablename__ = "reading_lists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    last_fetched = Column(String)  # ISO8601 string for demo; adjust as needed
    # Add relationships/fields as needed for UI, but do not migrate DB without user approval



