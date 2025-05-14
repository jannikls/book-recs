import math
from sqlalchemy.orm import Session
from . import models

def compute_cluster_niche_scores(session: Session, cluster_id: int):
    """
    Compute and upsert niche scores for all books in a cluster.
    - Queries all UserBook where user belongs to the cluster
    - Aggregates read_count per book
    - niche_score = 1 / log(1 + read_count)
    - Upserts into ClusterBook
    """
    # Find all users in the cluster
    cluster = session.query(models.Cluster).filter_by(id=cluster_id).first()
    if not cluster:
        return
    # Assuming a cluster.users relationship exists (adjust if not)
    user_ids = [u.id for u in getattr(cluster, 'users', [])]
    if not user_ids:
        return
    # Query all UserBook where user is in cluster
    userbooks = session.query(models.UserBook).filter(models.UserBook.user_id.in_(user_ids)).all()
    # Aggregate read_count per book
    book_counts = {}
    for ub in userbooks:
        book_counts[ub.book_id] = book_counts.get(ub.book_id, 0) + 1
    # Compute niche_score and upsert into ClusterBook
    for book_id, read_count in book_counts.items():
        niche_score = 1 / math.log(1 + read_count)
        cb = session.query(models.ClusterBook).filter_by(cluster_id=cluster_id, book_id=book_id).first()
        if cb:
            cb.read_count = read_count
            cb.niche_score = niche_score
        else:
            cb = models.ClusterBook(cluster_id=cluster_id, book_id=book_id, read_count=read_count, niche_score=niche_score)
            session.add(cb)
    session.commit()
