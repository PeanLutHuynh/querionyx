# Implementation Configuration

## rag

- **chunk_size**: `800`
- **chunk_overlap**: `120`
- **embedding_model**: `"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"`
- **embedding_dimension**: `384`
- **embedding_multilingual**: `true`
- **bm25_k1**: `1.5`
- **bm25_b**: `0.75`
- **top_k_dense**: `5`
- **top_k_sparse**: `5`
- **final_top_k**: `3`
- **rrf_k**: `60.0`
- **vector_store**: `"ChromaDB cosine"`

## sql_safety

- **read_only_only**: `true`
- **disallowed_keywords**: `["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE", "COPY", "CALL", "DO"]`
- **database_session_readonly**: `true`

## hybrid

- **async_execution**: `"asyncio.gather when RuntimeConfig.parallel_enabled=True"`
- **fallback_modes**: `["NONE", "SQL_ONLY", "RAG_ONLY", "SQL_DOMINANT", "TEMPLATE_MERGE", "BOTH_FAILED"]`
- **branch_trace_fields**: `["rag_status", "sql_status", "fallback_mode", "rag_latency_ms", "sql_latency_ms", "fusion_latency_ms", "retrieved_chunks", "generated_sql", "sql_result"]`
