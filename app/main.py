from fastapi import FastAPI, HTTPException, UploadFile, File, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from . import models, schemas, db
from .faiss_store import FaissStore
from .book_enrichment import enrich_books
import pandas as pd
import io
import numpy as np

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/books/count")
def books_count():
    with db.get_db() as session:
        count = session.query(models.Book).count()
    return {"count": count}

@app.get("/books/sample")
def books_sample(has_desc: int = 0, has_vector: int = 0):
    with db.get_db() as session:
        q = session.query(models.Book)
        if has_desc:
            q = q.filter(models.Book.description != None).filter(models.Book.description != "")
        if has_vector:
            q = q.filter(models.Book.vector != None)
        exists = q.first() is not None
    return {"ok": exists}

@app.get("/userbook")
def get_userbook(user_id: int, book_id: int):
    with db.get_db() as session:
        ub = session.query(models.UserBook).filter_by(user_id=user_id, book_id=book_id).one_or_none()
        if ub:
            return {"user_id": user_id, "book_id": book_id, "rating": ub.rating}
        return {"user_id": user_id, "book_id": book_id, "rating": None}

@app.get("/recommendations", response_class=HTMLResponse)
def recommendations_page(request: Request):
    return templates.TemplateResponse("recommendations.html", {"request": request})

from .vector_tasks import q, encode_and_store_book_vector

@app.post("/feedback")
def feedback(payload: dict):
    user_id = payload.get("user_id")
    book_id = payload.get("book_id")
    rating = payload.get("rating")
    if not (user_id and book_id and rating):
        return JSONResponse(status_code=400, content={"detail": "Missing user_id, book_id, or rating."})
    with db.get_db() as session:
        user_book = session.query(models.UserBook).filter_by(user_id=user_id, book_id=book_id).one_or_none()
        if user_book:
            user_book.rating = rating
        else:
            user_book = models.UserBook(user_id=user_id, book_id=book_id, rating=rating)
            session.add(user_book)
        session.commit()
    # Enqueue embedding worker for this user's profile
    q.enqueue(encode_and_store_book_vector, book_id)
    return {"detail": "Feedback saved and embedding update enqueued."}

@app.on_event("startup")
def startup():
    db.init_db()
    FaissStore.init()

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload-csv")
def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        return JSONResponse(status_code=400, content={"detail": "Invalid file type. Please upload a CSV."})
    content = file.file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Error reading CSV: {e}"})
    required_cols = {"title", "author", "isbn", "description", "subjects", "rating"}
    if not required_cols.issubset(df.columns):
        return JSONResponse(status_code=400, content={"detail": f"Missing columns: {required_cols - set(df.columns)}"})
    with db.get_db() as session:
        upserted = 0
        for _, row in df.iterrows():
            book_dict = row.to_dict()
            # Ensure subjects is a list
            if isinstance(book_dict["subjects"], str):
                book_dict["subjects"] = [s.strip() for s in book_dict["subjects"].split(";")]
            stmt = (
                session.query(models.Book)
                .filter(models.Book.isbn == book_dict["isbn"])
                .one_or_none()
            )
            if stmt:
                for k, v in book_dict.items():
                    setattr(stmt, k, v)
            else:
                stmt = models.Book(**book_dict)
                session.add(stmt)
            upserted += 1
        session.commit()
    # Launch enrichment background task
    background_tasks.add_task(enrich_books, next(db.get_db()))
    return {"detail": f"Successfully upserted {upserted} books. Enrichment started in background."}

@app.post("/books/", response_model=schemas.Book)
def add_book(book: schemas.BookCreate):
    with db.get_db() as session:
        db_book = db.create_book(session, book)
        FaissStore.add_book_vector(db_book.id, book.vector)
        return db_book

@app.get("/recommendations/", response_model=list[schemas.Book])
def recommend_books(query_vector: list[float], top_k: int = 5):
    ids = FaissStore.query(query_vector, top_k)
    with db.get_db() as session:
        return db.get_books_by_ids(session, ids)

@app.get("/profile")
def user_profile(user_id: int = Query(...)):
    with db.get_db() as session:
        # Get all UserBook with rating >= 4
        user_books = session.query(models.UserBook).filter(
            models.UserBook.user_id == user_id,
            models.UserBook.rating >= 4
        ).all()
        if not user_books:
            return JSONResponse(status_code=404, content={"detail": "No highly rated books for this user."})
        # Get vectors for these books
        book_ids = [ub.book_id for ub in user_books]
        books = session.query(models.Book).filter(models.Book.id.in_(book_ids)).all()
        vectors = [b.vector for b in books if b.vector]
        if not vectors:
            return JSONResponse(status_code=404, content={"detail": "No vectors found for user's books."})
        centroid = np.mean(np.array(vectors), axis=0).tolist()
        return {"user_id": user_id, "taste_vector": centroid}

@app.get("/recommend", response_model=list[schemas.Book])
def recommend_for_user(user_id: int = Query(...), k: int = Query(10)):
    with db.get_db() as session:
        # 1. Compute user taste vector
        user_books = session.query(models.UserBook).filter(
            models.UserBook.user_id == user_id,
            models.UserBook.rating >= 4
        ).all()
        if not user_books:
            raise HTTPException(status_code=404, detail="No highly rated books for this user.")
        book_ids = [ub.book_id for ub in user_books]
        books = session.query(models.Book).filter(models.Book.id.in_(book_ids)).all()
        vectors = [b.vector for b in books if b.vector]
        if not vectors:
            raise HTTPException(status_code=404, detail="No vectors found for user's books.")
        taste_vector = np.mean(np.array(vectors), axis=0).tolist()
        # 2. Query FAISS for top (k*3) nearest (to allow for filtering/boosting)
        candidate_ids = FaissStore.query(taste_vector, top_k=k*3)
        # 3. Filter out books the user has already read/rated
        read_ids = set(book_ids)
        candidates = session.query(models.Book).filter(models.Book.id.in_(candidate_ids)).all()
        filtered = [b for b in candidates if b.id not in read_ids]
        # 4. Recency and diversity boosts
        # Recency: prefer books with higher id (assuming id increments with time)
        filtered.sort(key=lambda b: (b.rating or 0, b.id), reverse=True)
        # Diversity: shuffle top 2*k and pick every other for more variety
        diverse = filtered[:2*k]
        import random
        random.shuffle(diverse)
        diverse = diverse[:k]
        # 5. Return as list of Book schemas
        return [schemas.Book.from_orm(b) for b in diverse]
