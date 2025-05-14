import requests
from sqlalchemy.orm import Session
from .models import Book
import time

GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"
OPENLIBRARY_API = "https://openlibrary.org/api/books"


def enrich_books(session: Session, batch_size: int = 10, delay: float = 1.0):
    books = session.query(Book).filter(
        (Book.description == None) | (Book.subjects == None) | (Book.subjects == [])
    ).all()
    for i in range(0, len(books), batch_size):
        batch = books[i:i+batch_size]
        for book in batch:
            info = fetch_book_info(book)
            if info:
                if not book.description and info.get("description"):
                    book.description = info["description"]
                if (not book.subjects or book.subjects == []) and info.get("subjects"):
                    book.subjects = info["subjects"]
        session.commit()
        time.sleep(delay)

def fetch_book_info(book: Book):
    # Try Google Books API first
    params = {"q": f"isbn:{book.isbn}"}
    try:
        resp = requests.get(GOOGLE_BOOKS_API, params=params, timeout=5)
        data = resp.json()
        if data.get("items"):
            volume = data["items"][0]["volumeInfo"]
            description = volume.get("description")
            subjects = volume.get("categories")
            return {"description": description, "subjects": subjects}
    except Exception:
        pass
    # Fallback to Open Library
    params = {"bibkeys": f"ISBN:{book.isbn}", "format": "json", "jscmd": "data"}
    try:
        resp = requests.get(OPENLIBRARY_API, params=params, timeout=5)
        data = resp.json()
        key = f"ISBN:{book.isbn}"
        if key in data:
            entry = data[key]
            description = entry.get("description")
            if isinstance(description, dict):
                description = description.get("value")
            subjects = [s["name"] for s in entry.get("subjects", [])]
            return {"description": description, "subjects": subjects}
    except Exception:
        pass
    return None
