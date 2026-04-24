# PAPER NOTES

---

## 1. Nền tảng Kiến trúc RAG Nguyên thủy

**Nghiên cứu:**  
*Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (Lewis et al., 2020)

### Tóm tắt & Insight
Bài báo đặt nền móng cho khái niệm RAG, giải quyết bài toán "ảo giác" (hallucination) và sự lạc hậu kiến thức của các Mô hình Ngôn ngữ Lớn (LLM) bằng cách kết hợp:
- **Parametric memory** (bộ nhớ tham số)
- **Non-parametric memory** (bộ nhớ phi tham số)

**Insight cốt lõi:**  
LLM không cần phải học thuộc lòng mọi thứ; khả năng hiểu ngôn ngữ có thể tách rời khỏi kho tri thức, giúp cập nhật linh hoạt mà không cần huấn luyện lại.

### Kỹ thuật trọng tâm
- Kiến trúc **Retrieve-then-Generate**
- **Dense Passage Retriever (DPR)** để tìm kiếm vector
- Mô hình **seq2seq (BART)** để sinh câu trả lời
- Hai chiến lược:
  - RAG-Sequence
  - RAG-Token

### Hạn chế
- Kiến trúc tuyến tính một chiều
- Fixed-size chunking (100 từ) phá vỡ cấu trúc logic
- Không xử lý dữ liệu có cấu trúc
- Thiếu multi-hop reasoning

### Đóng góp vào Querionyx
- Cơ sở lý luận cho RAG pipeline xử lý PDF
- Chứng minh cần chuyển từ **Naive RAG → Semantic Chunking + Hybrid**

---

## 2. Khai thác Dữ liệu Có cấu trúc qua Text-to-SQL

**Nghiên cứu:**  
*Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task* (Yu et al., 2018)

### Tóm tắt & Insight
Spider đánh giá khả năng chuyển ngôn ngữ tự nhiên thành SQL trên CSDL phức tạp.

**Insight cốt lõi:**  
Nút thắt không phải là cú pháp SQL, mà là:
- Schema linking
- Hiểu JOIN phức tạp

### Kỹ thuật trọng tâm
- Exact Matching
- Component Matching
- Phân loại độ khó truy vấn (JOIN, GROUP BY, nested queries)

### Hạn chế
- Loại bỏ câu hỏi mơ hồ
- Không xử lý business logic ngầm
- Không đánh giá value string thực tế

### Đóng góp vào Querionyx
- Định hình module Text-to-SQL (Northwind)
- Làm rõ nhu cầu **HYBRID Query Handler**
  - Dùng RAG để giải nghĩa trước khi truy vấn SQL

---

## 3. Sự tiến hóa của RAG trong Môi trường Doanh nghiệp

**Nghiên cứu:**  
*Retrieval-Augmented Generation for Large Language Models: A Survey* (Gao et al., 2023)

### Tóm tắt & Insight
Hệ thống hóa sự phát triển:
- Naive RAG → Advanced RAG → Modular RAG

**Insight cốt lõi:**  
Pipeline tuyến tính đã lỗi thời → cần hệ sinh thái linh hoạt

### Kỹ thuật trọng tâm
- Query Rewrite
- Query Routing
- Hybrid Search (Sparse + Dense)
- Context Compression (giảm “Lost in the middle”)

### Hạn chế
- Tăng độ phức tạp
- Tăng latency
- Khó orchestration
- Hợp nhất dữ liệu dị đồng vẫn là bài toán mở

### Đóng góp vào Querionyx
- Xác nhận chọn **Hybrid Search (Dense + BM25 + RRF)**
- Áp dụng kiến trúc **Multi-pipeline**

---

## 4. Kiến trúc Định tuyến và Thực thi Linh hoạt (Modular RAG)

**Nghiên cứu:**  
*Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable Frameworks* (Gao et al., 2024)

### Tóm tắt & Insight
Đề xuất RAG dạng mô-đun “LEGO”.

**Insight cốt lõi:**  
Hệ thống AI = tập hợp multi-module  
→ Routing + Branching + Fusion là chìa khóa

### Kỹ thuật trọng tâm
- Routing:
  - Rule-based
  - Semantic (LLM-based)
- Parallel execution (Branching)
- LLM Fusion

### Hạn chế
- Khó đảm bảo robustness
- Nguy cơ hallucination khi fusion xung đột

### Đóng góp vào Querionyx
- Thiết kế:
  - Adaptive Query Router
  - HYBRID Handler
- Routing 2 lớp:
  - Rule-based
  - LLM-based (confidence score)
- Áp dụng:
  - Parallel Execution
  - Coherent Merge

---

## 5. Khung Đánh giá Tự động Phi tham chiếu (RAGAS)

**Nghiên cứu:**  
*RAGAS: Automated Evaluation of Retrieval Augmented Generation* (Es et al., 2023)

### Tóm tắt & Insight
Giải quyết thiếu dữ liệu nhãn bằng **LLM-as-a-judge**

**Insight cốt lõi:**  
Không thể đánh giá RAG bằng 1 metric → cần tách thành:
- Generation Quality
- Retrieval Quality
- Context Alignment

### Kỹ thuật trọng tâm
4 metrics:
- Faithfulness
- Answer Relevance
- Context Precision
- Context Recall

### Hạn chế
- Giảm hiệu quả với long context
- Không hỗ trợ hybrid data (text + table)

### Đóng góp vào Querionyx
- Dùng cho đánh giá **Answer Quality (Layer 2)**
- Bổ sung:
  - Manual Evaluation (Cohen’s Kappa)
  - HYBRID Correctness / Coherence