# Book Recommender App

A modern, full-stack book recommendation system using FastAPI, PostgreSQL, Redis, FAISS, and Windsurf frontend. Import your Goodreads library, get tailored recommendations, and give feedback to improve your results.

## Social Clusters & Wrapped Dashboard

### Creating Clusters
- Use the admin interface or SQL to create a new cluster:
  ```sql
  INSERT INTO clusters (name) VALUES ('ML Club');
  ```
- (If implemented) Add users to clusters via a join table or admin panel.

### Importing Users & Libraries
- Upload your Goodreads CSV on the dashboard or use the `/upload-csv` endpoint.
- Users and their books will be imported and linked.

### Running the Wrapped Dashboard
- Start the FastAPI server:
  ```bash
  uvicorn app.main:app --reload
  ```
- Visit `/dashboard` for stats and visualizations.
- For cluster niche spots: `/clusters/<cluster_id>/niche-spots`
- For network graph: `/clusters/<cluster_id>/network`
- Use the Share button to export and share your cluster's "Wrapped".

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
