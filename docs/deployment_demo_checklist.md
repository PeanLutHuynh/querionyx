# Querionyx Deployment Demo Checklist

## Required Files

The Render backend needs this tracked file for lightweight RAG:

```text
data/processed/chunks_recursive.pkl
```

It contains chunks for:

- `fpt_2023.pdf`, `fpt_2024.pdf`, `fpt_2025.pdf`
- `masan_2023.pdf`, `masan_2024.pdf`, `masan_2025.pdf`
- `vinamilk_2023.pdf`, `vinamilk_2024.pdf`, `vinamilk_2025.pdf`

The raw PDFs can stay in Supabase Storage. The current deployed backend does not read the bucket directly; it reads the processed pickle above.

## Render Environment

Use these values for a stable demo:

```env
ENABLE_HEAVY_RAG=0
QUERIONYX_LIGHTWEIGHT_RAG=1
QUERIONYX_MERGE_LLM_ENABLED=0
QUERIONYX_USE_LLM_ROUTER=0
QUERIONYX_LIGHTWEIGHT_RAG_MS=4000
QUERIONYX_SQL_EXECUTION_MS=5000
QUERIONYX_END_TO_END_MS=10000
PGDATABASE=postgres
PGHOST=aws-1-ap-northeast-1.pooler.supabase.com
PGPORT=6543
PGSSLMODE=require
PGUSER=postgres.ycgdvyapkgeekrqqxkle
```

Set `PGPASSWORD` in Render as a secret environment variable. Rotate it if it was pasted into chat or shared anywhere.

## Vercel Environment

```env
NEXT_PUBLIC_API_BASE=https://YOUR_RENDER_BACKEND.onrender.com
```

Redeploy Vercel after changing this value.

## No-Ollama Demo Mode

Render does not run Ollama in this deployment. Keep these disabled:

```env
ENABLE_HEAVY_RAG=0
QUERIONYX_LIGHTWEIGHT_RAG=1
QUERIONYX_MERGE_LLM_ENABLED=0
QUERIONYX_USE_LLM_ROUTER=0
```

Expected behavior:

- SQL answers execute against Supabase Postgres.
- RAG answers are deterministic extractive summaries from `chunks_recursive.pkl`.
- Unsupported or low-confidence RAG questions should return: `Tôi không có đủ thông tin đáng tin cậy để trả lời câu hỏi này.`
- The first query after a Render cold start can be slower; repeat the same prompt once to demonstrate cache behavior.

## Health Checks

Open:

```text
https://YOUR_RENDER_BACKEND.onrender.com/health
```

Expected:

```json
{
  "status": "ok",
  "db_status": "ok",
  "rag_status": {
    "chunks_file": "ok",
    "chunk_count": 9670
  }
}
```

Open:

```text
https://YOUR_RENDER_BACKEND.onrender.com/metrics
```

After sending queries from Vercel, `request_count` should increase.

## Safe Demo Prompts

Use English or Vietnamese for SQL if the question is one of the supported fast-path shapes. For the smoothest live demo, use English for SQL ranking questions and Vietnamese for annual-report RAG questions.

SQL:

```text
Có bao nhiêu sản phẩm trong cơ sở dữ liệu?
Tổng số đơn hàng là bao nhiêu?
Liệt kê top 5 sản phẩm có giá cao nhất.
Top 5 customers by order count.
Top 5 customers by number of orders.
What is the best product by sold count?
Top 1 product by count.
Top 5 products by number of orders.
Sản phẩm bán chạy nhất theo số lượng là gì?
```

RAG:

```text
Tóm tắt rủi ro trong báo cáo của FPT.
Chiến lược tăng trưởng của Vinamilk là gì?
Masan đề cập cơ hội nào trong tài liệu?
Ban lãnh đạo FPT gồm những ai?
```

Unsupported-question test:

```text
Công thức bí mật sản xuất sữa của Vinamilk là gì?
```

## Demo Query Guidance

- Prefer company-specific RAG questions: include `FPT`, `Vinamilk`, or `Masan` plus a topic like `rủi ro`, `chiến lược`, `cơ hội`, or `ban lãnh đạo`.
- Prefer explicit SQL metric words: `top`, `count`, `number of orders`, `sold count`, `bao nhiêu`, `tổng`, `bán chạy`, `số lượng`.
- Avoid very open-ended prompts such as `Tell me about FPT`; ask for one topic at a time.
- Do not rely on Ollama-backed fallback planning on Render. If a SQL demo prompt matters, add or verify a deterministic fast path in `src/sql/text_to_sql.py`.
- You can warm the in-memory response cache before presenting by running the main demo prompts once. The cache is useful for repeat latency, but it is not persistent across Render restarts.

## No-Ollama Readiness Audit

Before pushing a demo build, run:

```bash
python scripts/audit_no_ollama_readiness.py
```

Target result:

```text
route_accuracy: 100%
no_ollama_safe_rate: 100%
sql_fast_path: 100 / 100 SQL-needed benchmark queries
issues: {}
```

This audit does not call the database, embeddings, or any LLM. It verifies that the 150-query benchmark routes correctly and that SQL/HYBRID questions have deterministic SQL fast paths for Render.

## Demo Rule

Do not paste the system prompt into the chat box. The chat box is for user questions only.

## Redeploy Order

1. Push backend changes and redeploy Render.
2. Confirm `/health` shows `db_status: ok` and `rag_status.chunks_file: ok`.
3. Push frontend changes and redeploy Vercel.
4. Open the Vercel app and run one SQL prompt, one RAG prompt, and the unsupported-question prompt.
