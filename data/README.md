# Data Layout

Only the compressed chunk corpus required by the no-Ollama demo is versioned.
Local models, vector indexes, raw documents, and response caches may remain in
a complete workspace for faster startup. They are excluded from Git and from
evaluation provenance.

| Path | Git | Purpose |
| --- | --- | --- |
| `processed/chunks_recursive.json.gz` | Tracked | 9,670 validated annual-report chunks used by lightweight RAG |
| `source_manifest.json` | Tracked | SHA-256 checksums for the nine source PDFs and processed corpus |
| `raw/annual_reports/` | Ignored | Original PDFs; obtain from the companies' investor-report sources |
| `models/` | Ignored | Downloaded sentence-transformer cache |
| `chroma_db/` | Ignored | Rebuildable dense-vector index |
| `cache/` | Ignored | Runtime Text-to-SQL cache; never treated as knowledge or evidence |

The API runs lightweight RAG directly from the tracked JSON gzip file. Install
`requirements-research.txt` and run `python -m src.data_prep.reindex_chromadb`
only when reproducing dense-retrieval experiments.

The PDF files are intentionally not redistributed. Place exact copies under
`data/raw/annual_reports/` and compare their hashes with
`data/source_manifest.json` before regenerating the corpus.
