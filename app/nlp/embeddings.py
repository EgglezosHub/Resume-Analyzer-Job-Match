# app/nlp/embeddings.py
from __future__ import annotations
from functools import lru_cache
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import settings

@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    # Reads SENTENCE_MODEL via Settings.sentence_model
    return SentenceTransformer(settings.sentence_model)

def embed(text: str) -> np.ndarray:
    model = get_model()
    v = model.encode([text], normalize_embeddings=True)
    return v[0]

def embed_many(texts: List[str]) -> np.ndarray:
    model = get_model()
    return model.encode(texts, normalize_embeddings=True)

