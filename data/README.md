# data/

Coloque aqui os documentos que serão indexados: `.html`, `.txt` ou `.pdf`.

Se a pasta estiver vazia, o `ingest` baixa a Lei 14.133/2021 do site do Planalto
(`lei_14133.html`) automaticamente.

Para indexar um edital, copie o PDF para cá e rode `docker compose run --rm ingest`.
Editais não têm a estrutura de artigos da lei, então eles caem no chunking por
parágrafos (veja `ingest/parse.py`).

Use apenas documentos públicos. Esta pasta fica fora do versionamento.
