import os
from rq import Queue
from redis import Redis
from sentence_transformers import SentenceTransformer
from .models import Book, UserBook
from .faiss_store import FaissStore
FaissStore.init()
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Setup Redis connection and RQ queue
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(redis_url)
q = Queue('book-encoding', connection=redis_conn)

# Load sentence-transformers model only once per worker
model = SentenceTransformer('all-mpnet-base-v2')

# SQLAlchemy setup (reuse app's DATABASE_URL)
db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def encode_and_store_book_vector(book_id):
    session = SessionLocal()
    book = session.query(Book).filter(Book.id == book_id).first()
    if not book:
        session.close()
        return
    # Compose the text
    text = f"{book.title} {book.description or ''} {book.author or ''} {'; '.join(book.subjects or [])}"
    vector = model.encode([text])[0].tolist()
    # Store vector in FAISS
    FaissStore.add_book_vector(book.id, vector)
    # Persist vector in DB
    book.vector = vector
    session.commit()
    print(f"Enriched book {book.id}: {book.title}")
    session.close()

def enqueue_all_books():
    session = SessionLocal()
    # Enqueue all books without a vector
    books = session.query(Book).filter(Book.vector == None).all()
    for book in books:
        q.enqueue(encode_and_store_book_vector, book.id)
    session.close()
