"""FastAPI entrypoint for Querionyx V3 production deployment."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.query_service import QueryService


app = FastAPI(title="Querionyx V3 API", version="0.7.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

query_service = QueryService()


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    debug: bool = False


@app.post("/query")
async def query(request: QueryRequest):
    return await query_service.query(request.question, debug=request.debug)


@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    return StreamingResponse(
        query_service.stream_query(request.question, debug=request.debug),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/upload")
async def upload(file: UploadFile = File(...), embed: Optional[bool] = Form(False)):
    content = await file.read()
    return await query_service.upload_pdf(file.filename or "upload.pdf", content, embed=bool(embed))


@app.get("/health")
def health():
    return query_service.health()


@app.get("/metrics")
def metrics():
    return query_service.metrics_snapshot()
