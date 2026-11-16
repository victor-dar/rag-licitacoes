import argparse
import logging

from .download import baixar_lei
from .pipeline import indexar


def main():
    ap = argparse.ArgumentParser(description="Indexa os documentos de data/ no Qdrant")
    ap.add_argument("--rebaixar", action="store_true", help="baixa a lei de novo")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.rebaixar:
        baixar_lei(forcar=True)
    total = indexar()
    logging.info("pronto: %d chunks na coleção", total)


if __name__ == "__main__":
    main()
