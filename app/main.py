from fastapi import FastAPI, HTTPException, UploadFile, File, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from . import models, schemas, db
from .faiss_store import FaissStore
from .book_enrichment import enrich_books
from .vector_tasks import q, encode_and_store_book_vector
import pandas as pd
import io
import numpy as np

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

from fastapi.responses import HTMLResponse
import io
import base64
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from sklearn.metrics.pairwise import cosine_similarity

@app.get("/missing-subjects")
def missing_subjects():
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        books = session.query(models.Book).filter((models.Book.subjects == None) | (models.Book.subjects == [])).all()
        return [{
            'id': b.id,
            'title': b.title,
            'author': b.author,
            'isbn': b.isbn
        } for b in books]
    finally:
        session_gen.close()

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        num_users = session.query(models.User).count()
        num_libraries = session.query(models.UserBook.user_id).distinct().count()
        num_books = session.query(models.Book).count()
        num_enriched_desc = session.query(models.Book).filter(models.Book.description != None, models.Book.description != '').count()
        num_enriched_subjects = session.query(models.Book).filter(models.Book.subjects != None, models.Book.subjects != []).count()
        num_vectors = session.query(models.Book).filter(models.Book.vector != None).count()
        # Vector visualization
        books_with_vectors = session.query(models.Book).filter(models.Book.vector != None).all()
        vectors = [b.vector for b in books_with_vectors if b.vector]
        titles = [b.title for b in books_with_vectors if b.vector]
        img_html = ""
        viz_method = 'umap'
        if vectors:
            arr = np.array(vectors)
            if arr.shape[0] > 1:
                try:
                    if viz_method == 'tsne':
                        reducer = TSNE(n_components=2, random_state=42)
                        X = reducer.fit_transform(arr)
                    else:
                        try:
                            import umap
                            reducer = umap.UMAP(n_components=2, random_state=42)
                            X = reducer.fit_transform(arr)
                        except Exception:
                            reducer = PCA(n_components=2)
                            X = reducer.fit_transform(arr)
                    fig, ax = plt.subplots()
                    ax.scatter(X[:,0], X[:,1], alpha=0.6)
                    for i, title in enumerate(titles[:30]):
                        ax.annotate(title[:20], (X[i,0], X[i,1]), fontsize=7, alpha=0.7)
                    ax.set_title(f'Book Vectors (2D)')
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    plt.close(fig)
                    buf.seek(0)
                    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                    img_html = f'<img src="data:image/png;base64,{img_base64}" style="max-width:700px;"/>'
                except Exception as e:
                    img_html = f'<div style="color:red;">Vector visualization failed: {str(e)}</div>'

        # Quantitative sanity check: avg similarity for 10 known-similar books vs random pairs
        sim_html = ""
        sim_pairs_html = ""
        if len(vectors) > 5:
            try:
                sim_matrix = cosine_similarity(arr)
                np.fill_diagonal(sim_matrix, -2)
                # Find top 5 most similar pairs
                sim_indices = np.dstack(np.unravel_index(np.argsort(sim_matrix.ravel())[::-1], sim_matrix.shape))[0]
                top_sim = []
                used = set()
                for i, j in sim_indices:
                    if len(top_sim) >= 5:
                        break
                    if i < j and (i,j) not in used:
                        top_sim.append((i, j, sim_matrix[i, j]))
                        used.add((i, j))
                # Find top 5 most dissimilar pairs
                dissim_indices = np.dstack(np.unravel_index(np.argsort(sim_matrix.ravel()), sim_matrix.shape))[0]
                top_dissim = []
                used = set()
                for i, j in dissim_indices:
                    if len(top_dissim) >= 5:
                        break
                    if i < j and (i,j) not in used:
                        top_dissim.append((i, j, sim_matrix[i, j]))
                        used.add((i, j))
                sim_pairs_html = "<h4>Top 5 Most Similar Book Pairs</h4><ol>"
                for i, j, score in top_sim:
                    sim_pairs_html += f"<li><b>{titles[i]}</b> &mdash; <b>{titles[j]}</b> (<i>{score:.2f}</i>)</li>"
                sim_pairs_html += "</ol><h4>Top 5 Most Dissimilar Book Pairs</h4><ol>"
                for i, j, score in top_dissim:
                    sim_pairs_html += f"<li><b>{titles[i]}</b> &mdash; <b>{titles[j]}</b> (<i>{score:.2f}</i>)</li>"
                sim_pairs_html += "</ol>"
            except Exception as e:
                sim_pairs_html = f'<div style="color:red;">Similarity calculation failed: {str(e)}</div>'
        if len(vectors) > 15:
            # Pick 10 random books as 'similar' (for demo), compare their pairwise sim to random pairs
            import random
            idxs = random.sample(range(len(vectors)), 10)
            sim_books = [vectors[i] for i in idxs]
            sim_matrix = cosine_similarity(sim_books)
            avg_sim = (np.sum(sim_matrix) - 10) / (10*9)  # exclude diagonal
            rand_idxs = random.sample(range(len(vectors)), 20)
            rand_pairs = [(vectors[rand_idxs[i]], vectors[rand_idxs[i+1]]) for i in range(0, 20, 2)]
            rand_sim = np.mean([cosine_similarity([a],[b])[0,0] for a,b in rand_pairs])
            sim_html = f"<ul><li>Avg similarity (10 random 'similar' books): <b>{avg_sim:.3f}</b></li>"
            sim_html += f"<li>Avg similarity (random pairs): <b>{rand_sim:.3f}</b></li></ul>"
        else:
            sim_html = "<i>Not enough vectors for similarity statistics.</i>"

            sim_html += "<i>For a real test, pick known-similar books by title/genre.</i>"
        html = f"""
        <h1>Book Catalog Dashboard</h1>
        <ul>
            <li><b>Number of users:</b> {num_users}</li>
            <li><b>Number of user libraries:</b> {num_libraries}</li>
            <li><b>Number of global books:</b> {num_books}</li>
            <li><b>Enriched Descriptions:</b> {num_enriched_desc}</li>
            <li><b>Enriched Subjects:</b> {num_enriched_subjects}</li>
            <li><b>Books with Vectors:</b> {num_vectors}</li>
        </ul>
        <h2>Book Vector Visualization</h2>
        {img_html or '<i>No vectors to visualize yet.</i>'}
        <h2>Vector Similarity QA</h2>
        {sim_html}
        {sim_pairs_html}
        """
        return HTMLResponse(content=html)
    finally:
        session_gen.close()

@app.get("/library", response_class=HTMLResponse)
def get_user_library(user_id: int = Query(...)):
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        user_books = session.query(models.UserBook).filter(models.UserBook.user_id == user_id).all()
        if not user_books:
            return HTMLResponse("<h2>No books found for this user.</h2>")
        rows = ""
        for ub in user_books:
            book = ub.book
            rows += f"""
                <tr>
                    <td>{book.title}</td>
                    <td>{book.author}</td>
                    <td>
                        <form method='post' action='/update-userbook' style='margin:0;'>
                            <input type='hidden' name='user_id' value='{user_id}' />
                            <input type='hidden' name='book_id' value='{book.id}' />
                            <input type='number' name='rating' min='0' max='5' step='0.5' value='{ub.rating or ''}' style='width:3em;' />
                            <select name='shelf'>
                                <option value='to-read' {'selected' if ub.shelf=='to-read' else ''}>to-read</option>
                                <option value='currently-reading' {'selected' if ub.shelf=='currently-reading' else ''}>currently-reading</option>
                                <option value='read' {'selected' if ub.shelf=='read' else ''}>read</option>
                            </select>
                            <button type='submit'>Save</button>
                        </form>
                    </td>
                    <td>{ub.shelf or ''}</td>
                    <td>{ub.review or ''}</td>
                </tr>
            """
        html = f"""
        <h2>User Library (user_id={user_id})</h2>
        <table border='1' cellpadding='5' style='border-collapse:collapse;'>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Author</th>
                    <th>Rating/Shelf</th>
                    <th>Current Shelf</th>
                    <th>Review</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
        return HTMLResponse(html)
    finally:
        session_gen.close()

@app.get("/books/count")
def books_count():
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        count = session.query(models.Book).count()
        return {"count": count}
    finally:
        session_gen.close()

@app.get("/books/sample")
def books_sample(has_desc: int = 0, has_vector: int = 0):
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        q = session.query(models.Book)
        if has_desc:
            q = q.filter(models.Book.description != None).filter(models.Book.description != "")
        if has_vector:
            q = q.filter(models.Book.vector != None)
        exists = q.first() is not None
        return {"ok": exists}
    finally:
        session_gen.close()

@app.get("/userbook")
def get_userbook(user_id: int, book_id: int):
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        ub = session.query(models.UserBook).filter_by(user_id=user_id, book_id=book_id).one_or_none()
        if ub:
            return {"user_id": user_id, "book_id": book_id, "rating": ub.rating}
        return {"user_id": user_id, "book_id": book_id, "rating": None}
    finally:
        session_gen.close()

@app.get("/recommendations", response_class=HTMLResponse)
def recommendations_page(request: Request):
    return templates.TemplateResponse("recommendations.html", {"request": request})

from .vector_tasks import q, encode_and_store_book_vector

from fastapi import Request, Form

@app.post("/feedback")
async def feedback(request: Request, user_id: int = Form(None), book_id: int = Form(None), rating: float = Form(None)):
    # Try form first
    if user_id is None or book_id is None or rating is None:
        # Try JSON body
        try:
            payload = await request.json()
            user_id = payload.get("user_id")
            book_id = payload.get("book_id")
            rating = payload.get("rating")
        except Exception:
            return JSONResponse(status_code=400, content={"detail": "Missing user_id, book_id, or rating."})
    if not (user_id and book_id and rating is not None):
        return JSONResponse(status_code=400, content={"detail": "Missing user_id, book_id, or rating."})
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        user_book = session.query(models.UserBook).filter_by(user_id=user_id, book_id=book_id).one_or_none()
        if user_book:
            user_book.rating = rating
        else:
            user_book = models.UserBook(user_id=user_id, book_id=book_id, rating=rating)
            session.add(user_book)
        session.commit()
    finally:
        session_gen.close()
    q.enqueue(encode_and_store_book_vector, book_id)
    # If form, redirect back to recommendations
    if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        return HTMLResponse("<div>Feedback saved. <a href=\"javascript:window.history.back()\">Back</a></div>")
    return {"detail": "Feedback saved and embedding update enqueued."}


@app.on_event("startup")
def startup():
    # Ensure all tables are created at startup (idempotent)
    db.init_db()
    FaissStore.init()


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        return JSONResponse(status_code=400, content={"detail": "Invalid file type. Please upload a CSV."})
    content = file.file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
        print('UPLOAD CSV DEBUG: Columns:', list(df.columns))
        print('UPLOAD CSV DEBUG: First 5 rows:')
        print(df.head().to_string())
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Error reading CSV: {e}"})

    # Normalize columns for app-native and Goodreads CSVs
    required_cols = {"title", "author", "isbn", "description", "Exclusive Shelf", "rating"}
    goodreads_map = {
        "title": "Title",
        "author": "Author",
        "isbn": "ISBN",
        "description": "My Review",
        "Exclusive Shelf": "Exclusive Shelf",
        "rating": "My Rating"
    }
    if not required_cols.issubset(df.columns):
        # Try Goodreads mapping
        if all(col in df.columns for col in goodreads_map.values()):
            df = df.rename(columns={v: k for k, v in goodreads_map.items()})
            def split_subjects(val):
                if pd.isna(val): return []
                if ';' in val:
                    return [s.strip() for s in val.split(';') if s.strip()]
                if ',' in val:
                    return [s.strip() for s in val.split(',') if s.strip()]
                return [val.strip()] if val.strip() else []
            df["subjects"] = df["subjects"].apply(split_subjects)
            # Fill missing description with empty string
            df["description"] = df["description"].fillna("")
        else:
            return JSONResponse(status_code=400, content={"detail": f"Missing columns: {required_cols - set(df.columns)} and not a recognized Goodreads export."})
    else:
        # Ensure subjects is a list
        def split_subjects(val):
            if isinstance(val, str):
                if ';' in val:
                    return [s.strip() for s in val.split(';') if s.strip()]
                if ',' in val:
                    return [s.strip() for s in val.split(',') if s.strip()]
                return [val.strip()] if val.strip() else []
            return []
        df["subjects"] = df["subjects"].apply(split_subjects)
    matched = 0
    upserted = 0
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        # Create a new user for this upload
        new_user = models.User()
        session.add(new_user)
        session.commit()
        user_id = new_user.id
        new_books = []
        book_fields = ["title", "author", "isbn", "description", "Exclusive Shelf", "rating"]
        surrogate_count = 0
        used_isbns = set()
        for _, row in df.iterrows():
            book_dict = {k: row[k] for k in book_fields if k in row}
            # Ensure rating is a float and not NaN/string/None
            try:
                rating_val = float(book_dict.get("rating", 0))
                if pd.isna(rating_val):
                    rating_val = 0
            except Exception:
                rating_val = 0
            book_dict["rating"] = rating_val
            # Clean ISBN: remove ='...' and any quotes/spaces
            isbn = str(book_dict.get("isbn", "")).strip()
            if isbn.startswith('="') and isbn.endswith('"'):
                isbn = isbn[2:-1]
            isbn = isbn.replace('"', '').replace("'", '').strip()
            # Deduplication: check for existing book
            book = session.query(models.Book).filter(models.Book.isbn == isbn).one_or_none()
            if book:
                matched += 1
            else:
                book = models.Book(title=row["title"], author=row["author"], isbn=isbn, description=row["description"], subjects=row["subjects"])
                session.add(book)
                session.flush()  # Ensure book.id is available
                if book.id is None:
                    continue
                upserted += 1
                new_books.append(book)
                # Enqueue vectorization for new book with robust logging and fallback
                try:
                    job = q.enqueue(encode_and_store_book_vector, book.id)
                    print(f"[VECTOR ENQUEUE] Book {book.id} enqueued for vectorization. Job id: {getattr(job, 'id', None)}")
                except Exception as e:
                    print(f"[VECTOR ENQUEUE ERROR] Book {book.id} failed to enqueue: {e}. Running direct vectorization.")
                    try:
                        encode_and_store_book_vector(book.id)
                        print(f"[VECTOR DIRECT] Book {book.id} vectorized directly.")
                    except Exception as e2:
                        print(f"[VECTOR DIRECT ERROR] Book {book.id} failed direct vectorization: {e2}")
            # Only link user if book.id is valid
            if not book or not book.id:
                continue
            # Link user to book in UserBook (user-specific library)
            shelf = str(book_dict.get("Exclusive Shelf", "to-read")).strip() or "to-read"
            review = str(book_dict.get("review", "")).strip() or None
            notes = str(book_dict.get("notes", "")).strip() or None
            user_book = session.query(models.UserBook).filter_by(user_id=user_id, book_id=book.id).one_or_none()
            if not user_book:
                user_book = models.UserBook(
                    user_id=user_id,
                    book_id=book.id,
                    rating=rating_val,
                    shelf=shelf,
                    review=review,
                    notes=notes
                )
                session.add(user_book)
            else:
                user_book.rating = rating_val
                user_book.shelf = shelf
                user_book.review = review
                user_book.notes = notes
        session.commit()
    finally:
        session_gen.close()
    # Launch enrichment background task
    background_tasks.add_task(enrich_books, next(db.get_db()), new_books)
    background_tasks.add_task(enrich_books, next(db.get_db()))
    return {"detail": f"Successfully upserted {upserted} books. Enrichment started in background.", "user_id": user_id}

@app.get("/library", response_class=HTMLResponse)
def get_user_library(user_id: int = Query(...)):
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        user_books = session.query(models.UserBook).filter(models.UserBook.user_id == user_id).all()
        db_book = db.create_book(session, book)
        FaissStore.add_book_vector(db_book.id, book.vector)
        # Associate the book with the user
        user_book = models.UserBook(user_id=user_id, book_id=db_book.id)
        session.add(user_book)
        session.commit()
        return db_book
    finally:
        session_gen.close()

@app.get("/recommendations/", response_model=list[schemas.Book])
def recommend_books(query_vector: list[float], top_k: int = 5):
    ids = FaissStore.query(query_vector, top_k)
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        return db.get_books_by_ids(session, ids)
    finally:
        session_gen.close()

@app.get("/profile")
def user_profile(user_id: int = Query(...)):
    session_gen = db.get_db()
    try:
        session = next(session_gen)
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
    finally:
        session_gen.close()

@app.get("/recommend", response_class=HTMLResponse)
def recommend_for_user(user_id: int = Query(...), k: int = Query(10)):
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        import random
        # 1. Compute user taste vector
        user_books = session.query(models.UserBook).filter(
            models.UserBook.user_id == user_id,
            models.UserBook.rating >= 4
        ).all()
        if not user_books:
            return HTMLResponse("<h2>No highly rated books for this user.</h2>")
        book_ids = [ub.book_id for ub in user_books]
        books = session.query(models.Book).filter(models.Book.id.in_(book_ids)).all()
        vectors = [b.vector for b in books if b.vector]
        if not vectors:
            return HTMLResponse("<h2>No vectors found for user's books.</h2>")
        centroid = np.mean(np.array(vectors), axis=0)
        # 2. Query FAISS for nearest books
        fallback_used = False
        try:
            ids = FaissStore.query(centroid, k+len(book_ids))
            candidates = session.query(models.Book).filter(models.Book.id.in_(ids)).all() if ids else []
        except Exception as e:
            candidates = []
        # 3. Remove already-read books
        read_ids = set(book_ids)
        filtered = [b for b in candidates if b.id not in read_ids]
        # 4. Recency and diversity boosts
        filtered.sort(key=lambda b: (getattr(b, 'rating', 0) or 0, b.id), reverse=True)
        diverse = filtered[:2*k]
        random.shuffle(diverse)
        diverse = diverse[:k]
        # Fallback: if no recs, pick random eligible books with vectors
        if not diverse:
            fallback_used = True
            eligible = session.query(models.Book).filter(models.Book.vector != None, ~models.Book.id.in_(read_ids)).all()
            random.shuffle(eligible)
            diverse = eligible[:k]
        if not diverse:
            return HTMLResponse("<h2>No recommendations found for this user.</h2>")
        rows = ""
        for b in diverse:
            rows += f"""
                <tr>
                    <td>{b.title}</td>
                    <td>{b.author}</td>
                    <td>{getattr(b, 'rating', '')}</td>
                    <td>{getattr(b, 'shelf', '')}</td>
                    <td>{b.description[:120]+'...' if b.description and len(b.description) > 120 else (b.description or '')}</td>
                    <td>
                        <form method='post' action='/feedback' style='margin:0;'>
                            <input type='hidden' name='user_id' value='{user_id}' />
                            <input type='hidden' name='book_id' value='{b.id}' />
                            <input type='hidden' name='rating' value='5' />
                            <button type='submit'>Upvote</button>
                        </form>
                        <form method='post' action='/feedback' style='margin:0;'>
                            <input type='hidden' name='user_id' value='{user_id}' />
                            <input type='hidden' name='book_id' value='{b.id}' />
                            <input type='hidden' name='rating' value='1' />
                            <button type='submit'>Downvote</button>
                        </form>
                    </td>
                </tr>
            """
        html = f"""
        <h2>Recommended Books (user_id={user_id})</h2>
        {('<div style=\"color:orange;\">[Fallback mode: showing random eligible books]</div>' if fallback_used else '')}
        <table border='1' cellpadding='5' style='border-collapse:collapse;'>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Author</th>
                    <th>Rating</th>
                    <th>Shelf</th>
                    <th>Description</th>
                    <th>Votes</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <button onclick="window.location.reload()">Get New Recommendations</button>
        """
        return HTMLResponse(html)
    finally:
        session_gen.close()

@app.get("/books", response_class=HTMLResponse)
def global_books():
    session_gen = db.get_db()
    try:
        session = next(session_gen)
        books = session.query(models.Book).all()
        if not books:
            return HTMLResponse("<h2>No books in global catalog.</h2>")
        rows = ""
        for b in books:
            desc = (b.description[:120] + '...') if b.description and len(b.description) > 120 else (b.description or '')
            rows += f"""
                <tr>
                    <td>{b.id}</td>
                    <td>{b.title}</td>
                    <td>{b.author}</td>
                    <td>{b.isbn or ''}</td>
                    <td>{'yes' if b.vector else 'no'}</td>
                    <td>{desc}</td>
                    <td>
                        <form method='post' action='/add-to-library' style='margin:0;'>
                            <input type='hidden' name='book_id' value='{b.id}' />
                            <input type='number' name='user_id' value='' min='1' required placeholder='User ID' style='width:5em;' />
                            <button type='submit'>Add to My Library</button>
                        </form>
                    </td>
                </tr>
            """
        html = f"""
        <h2>Global Book List</h2>
        <table border='1' cellpadding='5' style='border-collapse:collapse;'>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Author</th>
                    <th>ISBN</th>
                    <th>Vector?</th>
                    <th>Description</th>
                    <th>Add</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
        return HTMLResponse(html)
    finally:
        session_gen.close()
