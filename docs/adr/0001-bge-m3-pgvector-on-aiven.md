# Embed chunks with bge-m3 and store them in pgvector on the main Aiven database

DCE files are mostly French with some Arabic, so we embed chunks with `BAAI/bge-m3` (1024-dim, strong multilingual and Arabic retrieval) via sentence-transformers, accepting it is ~2–3× slower on CPU than `multilingual-e5-base`. Vectors live in the existing Aiven Postgres (pgvector extension) rather than a separate vector database, so chunks sit next to the tender records they cite and we run one managed database instead of two.

## Consequences

Changing the model means re-embedding every chunk and altering the `vector(1024)` column. To keep that cheap: every chunk records its `embedding_model`, model name and dimension come from config (`EMBEDDING_MODEL`, `EMBEDDING_DIM`), and all vector access goes through a `VectorStore` interface so the store can be swapped without touching the pipeline.
