# RAG Evaluation - 3 Version Comparison

**Timestamp**: 2026-05-09T06:32:29+07:00

## Performance Summary

| Version | Total | Successful | Success Rate | Precision | Recall | Latency (ms) |
|---------|-------|-----------|--------------|-----------|--------|--------------|
| rag_v1 | 50 | 47 | 0.9400 | 0.8158 | 0.8388 | 220.80 |
| rag_v2 | 50 | 49 | 0.9800 | 0.8878 | 0.8542 | 279.79 |
| rag_v3 | 50 | 49 | 0.9800 | 0.9004 | 0.8466 | 241.44 |

## Detailed Metrics

| Version | Drift Rate | Hard Negative Acc | Avg Context Chunks |
|---------|------------|-------------------|-------------------|
| rag_v1 | 0.0500 | 0.9200 | 4.14 |
| rag_v2 | 0.0500 | 0.9200 | 3.88 |
| rag_v3 | 0.0500 | 0.9200 | 3.76 |

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
