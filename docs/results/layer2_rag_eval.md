# RAG Evaluation - 3 Version Comparison

**Timestamp**: 2026-05-08T09:22:12+07:00

## Performance Summary

| Version | Total | Successful | Success Rate | Precision | Recall | Latency (ms) |
|---------|-------|-----------|--------------|-----------|--------|--------------|
| rag_v1 | 30 | 28 | 0.9333 | 0.8270 | 0.8583 | 237.22 |
| rag_v2 | 30 | 28 | 0.9333 | 0.8973 | 0.8500 | 260.36 |
| rag_v3 | 30 | 29 | 0.9667 | 0.9060 | 0.8450 | 251.57 |

## Detailed Metrics

| Version | Drift Rate | Hard Negative Acc | Avg Context Chunks |
|---------|------------|-------------------|-------------------|
| rag_v1 | 0.0500 | 0.9200 | 4.17 |
| rag_v2 | 0.0500 | 0.9200 | 3.97 |
| rag_v3 | 0.0500 | 0.9200 | 3.83 |

## Version Comparison

### RAG V1: Cosine + Recursive Chunking
- Baseline with cosine similarity only
- Recursive chunking strategy
- Simpler retrieval, potentially lower precision on boundary cases

### RAG V2: Hybrid Retrieval
- Combines dense (cosine) + sparse (BM25) retrieval
- Reciprocal Rank Fusion (RRF) fusion
- Improved precision through hybrid approach

### RAG V3: Semantic Chunking + Hybrid
- Advanced semantic chunking strategy
- Hybrid retrieval with learned fusion weights
- Best precision and recall tradeoff
