FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV ENABLE_HEAVY_RAG=0
ENV QUERIONYX_LIGHTWEIGHT_RAG=1
ENV QUERIONYX_MERGE_LLM_ENABLED=0
ENV QUERIONYX_USE_LLM_ROUTER=0

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

