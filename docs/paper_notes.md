# Paper Notes - Querionyx

## Hướng dẫn đọc
Khi đọc mỗi paper, hãy trả lời các câu hỏi sau:
1. **Vấn đề chính**: Paper giải quyết vấn đề gì?
2. **Phương pháp**: Cách tiếp cận chính là gì?
3. **Kết quả**: Performance chính của phương pháp?
4. **Liên quan Querionyx**: Điểm nào có thể áp dụng vào project?
5. **Research gap**: Vấn đề còn chưa giải quyết là gì?

---

## Lewis et al. (2020) - Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
- **Link**: https://arxiv.org/abs/2005.11401
- **Abstract**: RAG combines pre-trained parametric and non-parametric memory for open-domain QA
- **Vấn đề chính**: 
  - Parametric models khó truy cập/cập nhật tri thức
  - Không thể explain lý do cho câu trả lời
  
- **Phương pháp (RAG)**:
  - Dense Passage Retriever (DPR): lấy k relevant documents
  - Sequence-to-Sequence generator: sinh response từ document
  
- **Kết quả**:
  - Natural Questions: ...
  - TriviaQA: ...
  
- **Áp dụng vào Querionyx**:
  - [ ] Cấu trúc 2 module: retriever + generator
  - [ ] Sử dụng embedding để tìm relevant queries
  
- **Research gaps**:
  - [ ] Ghi chú những vấn đề chưa giải quyết

---

## Yu et al. (2018) - Spider: A Large-Scale Dataset for Complex and Cross-Domain Semantic Parsing
- **Link**: https://arxiv.org/abs/1809.08887
- **Abstract**: Tạo dataset 80K text-to-SQL queries trên 200+ databases
- **Vấn đề chính**:
  - Thiếu dataset lớn cho complex SQL understanding
  - Cần cross-domain semantic parsing evaluation
  
- **Dataset characteristics**:
  - Databases: ...
  - Queries: ...
  - Complexity metrics: ...
  
- **Áp dụng vào Querionyx**:
  - [ ] Cấu trúc tương tự dataset cho Northwind
  - [ ] Metrics evaluate SQL generation quality
  
- **Research gaps**:
  - [ ] Ghi chú

---

## Gao et al. (2023) - Retrieval-Augmented Generation for LLMs: A Survey
- **Link**: https://arxiv.org/abs/2312.10997
- **Abstract**: Comprehensive survey của RAG techniques và applications
- **Phân loại chính**:
  - Naive RAG: ...
  - Advanced RAG: ...
  - Modular RAG: ...
  
- **Key techniques**:
  - [ ] Chunking strategies
  - [ ] Retrieval ranking
  - [ ] Generation optimization
  
- **Áp dụng vào Querionyx**:
  - [ ] Xác định RAG type phù hợp
  - [ ] Selection strategies
  
- **Research gaps**:
  - [ ] Ghi chú

---

## Gao et al. (2024) - Modular RAG: Transforming RAG into Adaptive Modular Architectures
- **Link**: https://arxiv.org/abs/2407.21059
- **Abstract**: Mô hình modular cho phép customize từng component của RAG
- **Modular components**:
  - Query router
  - Multi retrievers
  - Fusion strategies
  - Adaptive generator
  
- **Innovations**:
  - [ ] Component independence
  - [ ] Routing mechanisms
  - [ ] Fallback strategies
  
- **Áp dụng vào Querionyx**:
  - [ ] Hybrid search (SQL + document retrieval)
  - [ ] Multi-step query routing
  
- **Research gaps**:
  - [ ] Ghi chú

---

## Es et al. (2023) - RAGAS: Automated Evaluation of RAG
- **Link**: https://arxiv.org/abs/2309.15217
- **Abstract**: Framework để tự động evaluate RAG systems bằng LLM
- **Metrics chính**:
  - **Faithfulness**: Retrieved docs được reflect trong response?
  - **Answer Relevancy**: Response trả lời câu hỏi?
  - **Context Recall**: Relevant context được retrieve?
  - **Context Precision**: Retrieved context có chứa nhiễu?
  
- **Implementation**:
  - Uses LLM để evaluate
  - Không cần ground truth
  
- **Áp dụng vào Querionyx**:
  - [ ] Evaluate SQL query correctness (analogous to answer relevancy)
  - [ ] Check document retrieval quality
  - [ ] Measure hybrid search effectiveness
  
- **Research gaps**:
  - [ ] Ghi chú

---

## Summary - Application to Querionyx
- **RAG Components** (Lewis 2020):
  - Retriever: Find relevant Northwind tables/schemas + documents
  - Generator: Convert to SQL queries + natural explanations
  
- **Dataset Benchmark** (Yu et al. 2018):
  - Test on complex multi-table queries
  - Cross-domain evaluation
  
- **Architecture Patterns** (Gao et al. 2023, 2024):
  - Choose Modular RAG with multiple retrievers
  - SQL retriever + Document retriever
  - Adaptive routing based on query type
  
- **Evaluation Strategy** (Es et al. 2023):
  - Measure faithfulness of SQL queries to requirements
  - Check context precision (retrieve only relevant tables)
  - Answer relevancy for generated explanations

- Research gap chua giai quyet: ...
