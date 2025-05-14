# Book Recommender App

A modern, full-stack book recommendation system using FastAPI, PostgreSQL, Redis, FAISS, and Windsurf frontend. Import your Goodreads library, get tailored recommendations, and give feedback to improve your results.

- Uses FAISS for fast vector similarity search

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start PostgreSQL and set the `DATABASE_URL` environment variable.
3. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (e.g. `postgresql+psycopg2://user:password@localhost:5432/bookrec`)

## Development
- Python 3.9+
- PostgreSQL 13+
- FAISS

---

MIT License
