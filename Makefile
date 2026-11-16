.PHONY: up down reindex eval test

up:
	docker compose up --build

down:
	docker compose down

reindex:
	docker compose run --rm ingest

eval:
	python eval/run_eval.py

test:
	python -m pytest -q
