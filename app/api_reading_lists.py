from fastapi import APIRouter, Body, Path, BackgroundTasks, Depends, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import models, db
from datetime import datetime

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

# --- In-memory storage for reading list items (no DB schema changes) ---
READING_LIST_ITEMS = {}  # {list_id: [book_dict, ...]}
READING_LIST_META = {}   # {list_id: {name, url, last_fetched}}

@router.get("/reading-lists", response_class=HTMLResponse)
@router.get("/reading-lists/", response_class=HTMLResponse)
def reading_lists_page(request: Request):
    return templates.TemplateResponse("reading_lists.html", {"request": request})

from fastapi.responses import RedirectResponse

@router.post("/reading-lists")
@router.post("/reading-lists/")
def create_reading_list(
    name: str = Form(...),
    url: str = Form(...),
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(db.get_db)
):
    # Check if a reading list with this URL already exists
    existing = session.query(models.ReadingList).filter(models.ReadingList.url == url).first()
    if existing:
        # Sync meta (in case server restarted)
        READING_LIST_META[existing.id] = {"name": existing.name, "url": existing.url, "last_fetched": existing.last_fetched}
        # Redirect to existing
        return RedirectResponse(f"/reading-lists/{existing.id}", status_code=303)
    rl = models.ReadingList(name=name, url=url, last_fetched=None)
    session.add(rl)
    session.commit()
    # Save meta for in-memory use
    READING_LIST_META[rl.id] = {"name": name, "url": url, "last_fetched": None}
    fetch_reading_list(rl.id)
    return RedirectResponse(f"/reading-lists/{rl.id}", status_code=303)

import httpx
from bs4 import BeautifulSoup
from datetime import datetime

def parse_title_author(text):
    # Very naive split, e.g. "Title by Author"
    if ' by ' in text:
        title, author = text.split(' by ', 1)
        return title.strip(), author.strip()
    return text.strip(), None

def upsert_book_via_openlibrary(title, author):
    # Stub: would call OpenLibrary API or internal upsert
    # Return a fake book object with id and dummy fields
    return type('Book', (), {
        'id': hash((title, author)) % 10**8,
        'title': title,
        'author': author,
        'cover_url': None,
        'niche_score': None,
        'isbn': None  # Ensure .isbn is always present for enrichment
    })

from app.book_enrichment import fetch_book_info

def fetch_reading_list(list_id: int, session=None):
    # Use in-memory meta if available
    meta = READING_LIST_META.get(list_id)
    url = meta["url"] if meta else "https://www.jannikschilling.com/bookshelf/"
    resp = httpx.get(url)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("ol li, ul li")
    books = []
    for idx, li in enumerate(items, start=1):
        text = li.get_text(strip=True)
        title, author = parse_title_author(text)
        book = upsert_book_via_openlibrary(title, author)
        # Enrich book with cover and description
        enrichment = fetch_book_info(book)
        books.append({
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "cover_url": enrichment.get("cover_url") or book.cover_url or "https://via.placeholder.com/56x84?text=No+Cover",
            "niche_score": book.niche_score,
            "description": enrichment.get("description")
        })
    READING_LIST_ITEMS[list_id] = books
    # Update meta
    if meta:
        meta["last_fetched"] = datetime.utcnow().isoformat()
    print(f"Fetched {len(books)} items from {url} for ReadingList {list_id}")

@router.get("/reading-lists/{list_id}", response_class=HTMLResponse)
def reading_list_detail(list_id: int, request: Request):
    meta = READING_LIST_META.get(list_id, {})
    items = READING_LIST_ITEMS.get(list_id)
    # If never fetched or missing items, fetch now
    if not items:
        fetch_reading_list(list_id)
        items = READING_LIST_ITEMS.get(list_id, [])
    context = {
        "request": request,
        "list": {
            "id": list_id,
            "name": meta.get("name", f"List {list_id}"),
            "url": meta.get("url", ""),
            "last_fetched": meta.get("last_fetched"),
            "items": items
        }
    }
    return templates.TemplateResponse("reading_list.html", context)

# API endpoint for JSON (if needed)
@router.get("/api/reading-lists/{list_id}")
def get_reading_list_json(list_id: int = Path(...)):
    meta = READING_LIST_META.get(list_id, {})
    items = READING_LIST_ITEMS.get(list_id, [])
    return {
        "id": list_id,
        "name": meta.get("name", f"List {list_id}"),
        "url": meta.get("url", ""),
        "last_fetched": meta.get("last_fetched"),
        "items": items
    }

@router.get("/api/reading-lists")
def list_reading_lists(session: Session = Depends(db.get_db)):
    # Query all ReadingList objects from DB
    lists = session.query(models.ReadingList).all()
    # Sync in-memory meta for all lists
    for rl in lists:
        if rl.id not in READING_LIST_META:
            READING_LIST_META[rl.id] = {"name": rl.name, "url": rl.url, "last_fetched": rl.last_fetched}
    return [
        {"id": rl.id, "name": rl.name, "url": rl.url, "last_fetched": rl.last_fetched}
        for rl in lists
    ]

@router.post("/reading-lists/{list_id}/items/{book_id}/add")
def add_to_library(list_id: int = Path(...), book_id: int = Path(...)):
    # Would create UserBook for current user
    return {"status": "ok"}
