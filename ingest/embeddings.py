from . import config

_modelo = None


def get_modelo():
    global _modelo
    if _modelo is None:
        from sentence_transformers import SentenceTransformer

        _modelo = SentenceTransformer(config.EMBED_MODEL)
    return _modelo


def _e5() -> bool:
    return "e5" in config.EMBED_MODEL.lower()


def dimensao() -> int:
    return get_modelo().get_sentence_embedding_dimension()


def embed_passagens(textos: list[str]):
    if _e5():
        textos = [f"passage: {t}" for t in textos]
    return get_modelo().encode(
        textos, normalize_embeddings=True, batch_size=32, show_progress_bar=False
    )


def embed_consulta(pergunta: str):
    if _e5():
        pergunta = f"query: {pergunta}"
    return get_modelo().encode(pergunta, normalize_embeddings=True)
