import faiss
import numpy as np
import os

class FaissStore:
    index = None
    id_map = {}
    vector_dim = 768  # all-mpnet-base-v2 outputs 768-dim vectors
    store_path = "faiss.index"

    @classmethod
    def init(cls):
        if os.path.exists(cls.store_path):
            cls.index = faiss.read_index(cls.store_path)
        else:
            cls.index = faiss.IndexFlatL2(cls.vector_dim)
        cls.id_map = {}

    @classmethod
    def add_book_vector(cls, book_id, vector):
        vec = np.array([vector]).astype('float32')
        cls.index.add(vec)
        cls.id_map[cls.index.ntotal - 1] = book_id
        faiss.write_index(cls.index, cls.store_path)

    @classmethod
    def query(cls, vector, top_k=5):
        vec = np.array([vector]).astype('float32')
        D, I = cls.index.search(vec, top_k)
        return [cls.id_map.get(i) for i in I[0] if i in cls.id_map]
