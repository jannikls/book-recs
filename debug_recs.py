from app.models import UserBook, Book
from app.db import get_db
from app.faiss_store import FaissStore
session = next(get_db())
users = session.query(UserBook.user_id).distinct().all()
books_with_vectors = session.query(Book).filter(Book.vector!=None).all()
print(f'Total books with vectors: {len(books_with_vectors)}')
faiss_missing = []
for b in books_with_vectors:
    res = FaissStore.query(b.vector, 1)
    if not res or res[0] != b.id:
        faiss_missing.append(b.id)
print('Books missing from FAISS index:', len(faiss_missing))
for (user_id,) in users:
    rated = session.query(UserBook).filter(UserBook.user_id==user_id, UserBook.rating>=4).count()
    print('User', user_id, ':', rated, 'highly rated books')
    rated_books = session.query(UserBook).filter(UserBook.user_id==user_id, UserBook.rating>=4).all()
    for ub in rated_books:
        print('  Book:', ub.book_id, ub.book.title if ub.book else None)
