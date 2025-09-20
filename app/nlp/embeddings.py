from sentence_transformers import SentenceTransformer
from app.core.config import settings


_model = None


def get_model() -> SentenceTransformer:
	global _model
	if _model is None:
		_model = SentenceTransformer(settings.sentence_model)
	return _model


def embed(text: str):
	model = get_model()
	return model.encode([text], normalize_embeddings=True)[0]
