import os
from pathlib import Path

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("COLLECTION", "licitacoes")
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

LEI_URL = os.getenv(
    "LEI_URL",
    "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/L14133.htm",
)
LEI_ARQUIVO = "lei_14133.html"
