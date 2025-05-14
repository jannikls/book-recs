from fastapi import APIRouter, Query, Path, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app import models, db

router = APIRouter()

@router.get("/clusters/{cluster_id}/niche-spots")
def get_niche_spots(cluster_id: int = Path(...), k: int = Query(10), session: Session = Depends(db.get_db)):
    # Fetch top-k ClusterBook by niche_score desc
    q = (
        session.query(models.ClusterBook, models.Book)
        .join(models.Book, models.ClusterBook.book_id == models.Book.id)
        .filter(models.ClusterBook.cluster_id == cluster_id)
        .order_by(models.ClusterBook.niche_score.desc())
        .limit(k)
    )
    result = []
    for cb, book in q:
        result.append({
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "cover_url": book.cover_url,
            "read_count": cb.read_count,
            "niche_score": cb.niche_score,
        })
    return JSONResponse(result)

from fastapi import BackgroundTasks, Body
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os, base64, io
from fastapi.responses import FileResponse
from app.tasks import compute_cluster_niche_scores

@router.get("/clusters/{cluster_id}/network")
def get_cluster_network(cluster_id: int = Path(...), session: Session = Depends(db.get_db)):
    # Load all books in cluster with embeddings and niche_score
    q = (
        session.query(models.ClusterBook, models.Book)
        .join(models.Book, models.ClusterBook.book_id == models.Book.id)
        .filter(models.ClusterBook.cluster_id == cluster_id)
    )
    nodes = []
    vectors = []
    id_map = {}
    for idx, (cb, book) in enumerate(q):
        nodes.append({
            "id": book.id,
            "title": book.title,
            "cover_url": book.cover_url,
            "niche_score": cb.niche_score,
        })
        id_map[book.id] = idx
        vectors.append(book.vector or [])
    # Compute edges
    edges = []
    if len(vectors) > 1:
        arr = np.array(vectors)
        sim = cosine_similarity(arr)
        n = len(nodes)
        for i in range(n):
            for j in range(i+1, n):
                if sim[i, j] > 0.8:
                    edges.append({"source": nodes[i]["id"], "target": nodes[j]["id"], "weight": float(sim[i, j])})
    return {"nodes": nodes, "edges": edges}

@router.post("/clusters/{cluster_id}/niche-spots/export")
def export_niche_spots(cluster_id: int = Path(...), payload: dict = Body(...)):
    # Accept SVG/PNG data from frontend, save to static, return URL
    img_data = payload.get("img_base64")
    if not img_data:
        return JSONResponse(status_code=400, content={"detail": "Missing image data"})
    img_bytes = base64.b64decode(img_data.split(",")[-1])
    static_dir = os.path.join(os.path.dirname(__file__), "static", "exports")
    os.makedirs(static_dir, exist_ok=True)
    out_path = os.path.join(static_dir, f"cluster{cluster_id}_niche_spots.png")
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    url = f"/static/exports/cluster{cluster_id}_niche_spots.png"
    return {"url": url}

# Example: hook background task on cluster creation or user import
# def create_cluster(..., background_tasks: BackgroundTasks):
#     ...
#     background_tasks.add_task(compute_cluster_niche_scores, cluster_id)
