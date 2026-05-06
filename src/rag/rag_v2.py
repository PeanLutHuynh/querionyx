"""RAG Pipeline V2 - Hybrid Search (Dense + Sparse with RRF Fusion).

Architecture:
- Bilingual user support: Vietnamese and English questions
- Embeddings: multilingual sentence-transformers model, cached locally
- Dense Retrieval: ChromaDB persistent collection with cosine similarity, top_k=5
- Sparse Retrieval: BM25 index on same chunks, top_k=5
- Fusion: Reciprocal Rank Fusion (RRF) with k=60, merge to final top-3
- Generation: Ollama qwen2.5:3b via LangChain OllamaLLM, max context = top-3 chunks
- Source Attribution: citation of filename + page number
- Anti-hallucination: fixed Vietnamese not-found response
"""

import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "chunks_recursive.pkl"
CHROMA_DB_PATH = PROJECT_ROOT / "data" / "chroma_db"
EMBEDDING_CACHE_DIR = PROJECT_ROOT / "data" / "models" / "sentence_transformers"
COLLECTION_NAME = "querionyx_v1"

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_LLM_MODEL = "qwen2.5:3b"
NOT_FOUND_MESSAGE = "Tôi không tìm thấy thông tin này trong tài liệu."
NOT_FOUND_MESSAGES = {
    "vi": NOT_FOUND_MESSAGE,
    "en": "I cannot find this information in the provided documents.",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

VIETNAMESE_CHARS = set(
    "àáảãạăằắẳẵặâầấẩẫậ"
    "èéẻẽẹêềếểễệ"
    "ìíỉĩị"
    "òóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữự"
    "ỳýỷỹỵđ"
)
VIETNAMESE_KEYWORDS = {
    "ai",
    "bao",
    "bao nhiêu",
    "báo cáo",
    "có",
    "của",
    "được",
    "gì",
    "không",
    "là",
    "nào",
    "như thế nào",
    "trong",
    "và",
    "về",
}


def detect_language(text: str) -> str:
    """Return ``vi`` for Vietnamese-looking text, otherwise ``en``."""
    text_lower = text.lower()

    if any(char in text_lower for char in VIETNAMESE_CHARS):
        return "vi"

    padded = f" {text_lower} "
    if any(f" {keyword} " in padded for keyword in VIETNAMESE_KEYWORDS):
        return "vi"

    return "en"


class RAGPipelineV2:
    """Hybrid search RAG with dense (ChromaDB) + sparse (BM25) retrieval and RRF fusion."""

    def __init__(
        self,
        embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
        llm_model: str = DEFAULT_LLM_MODEL,
        dense_top_k: int = 5,
        sparse_top_k: int = 5,
        final_top_k: int = 3,
        rrf_k: float = 60.0,
        ollama_base_url: Optional[str] = None,
        relevance_distance_threshold: float = 0.35,
        upsert_batch_size: int = 1000,
        encode_batch_size: int = 64,
        llm_timeout_seconds: int = 90,
        max_context_chars_per_chunk: int = 650,
        max_generation_chunks: int = 3,
    ):
        self.dense_top_k = dense_top_k
        self.sparse_top_k = sparse_top_k
        self.final_top_k = final_top_k
        self.rrf_k = rrf_k
        self.embedding_model_name = embedding_model_name
        self.llm_model = llm_model
        self.relevance_distance_threshold = relevance_distance_threshold
        self.upsert_batch_size = upsert_batch_size
        self.encode_batch_size = encode_batch_size
        self.llm_timeout_seconds = llm_timeout_seconds
        self.max_context_chars_per_chunk = max_context_chars_per_chunk
        self.max_generation_chunks = max_generation_chunks

        load_dotenv(PROJECT_ROOT / ".env")
        raw_ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.ollama_base_url = raw_ollama_base_url.replace("http://localhost", "http://127.0.0.1")
        self.ollama_base_url = self.ollama_base_url.replace("https://localhost", "http://127.0.0.1")

        print("Initializing RAG Pipeline V2 (Hybrid Search)...")
        print(f"  - Embedding model: {embedding_model_name}", flush=True)
        print(f"  - LLM: {llm_model} (qwen2.5:3b - fast & accurate)", flush=True)
        print(f"  - Dense retrieval: top_k={dense_top_k}", flush=True)
        print(f"  - Sparse retrieval: top_k={sparse_top_k}", flush=True)
        print(f"  - RRF fusion: k={rrf_k}, final_top_k={final_top_k}", flush=True)
        print(f"  - Vector store: {CHROMA_DB_PATH}", flush=True)

        print("  Loading embeddings model...", flush=True)
        EMBEDDING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.embeddings_model = SentenceTransformer(
            embedding_model_name,
            cache_folder=str(EMBEDDING_CACHE_DIR),
        )
        print(f"     Model loaded: {embedding_model_name}", flush=True)

        print("  Initializing ChromaDB...", flush=True)
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        print(f"     ChromaDB initialized at {CHROMA_DB_PATH}", flush=True)

        print("  Initializing Ollama LLM...", flush=True)
        self.llm = OllamaLLM(
            model=llm_model,
            base_url=self.ollama_base_url,
            temperature=0.1,
            num_predict=220,
            num_ctx=2048,
            sync_client_kwargs={"timeout": llm_timeout_seconds},
        )
        print(f"     Ollama endpoint: {self.ollama_base_url}", flush=True)

        self.collection = None
        self.chunks_data = None
        self.bm25_index = None
        self.tokenized_chunks = None

    def load_chunks(self, verbose: bool = True) -> int:
        """Load preprocessed chunks from pickle, index in ChromaDB, and build BM25 index."""
        if not CHUNKS_FILE.exists():
            raise FileNotFoundError(f"Chunks file not found: {CHUNKS_FILE}")

        if verbose:
            print(f"\nLoading chunks from {CHUNKS_FILE}...", flush=True)

        with open(CHUNKS_FILE, "rb") as f:
            chunks = pickle.load(f)

        if verbose:
            print(f"   Loaded {len(chunks)} chunks from pickle", flush=True)

        self.chunks_data = chunks
        existing_collections = [col.name for col in self.chroma_client.list_collections()]
        collection_metadata = {
            "hnsw:space": "cosine",
            "embedding_model": self.embedding_model_name,
            "chunks_file": str(CHUNKS_FILE.relative_to(PROJECT_ROOT)),
        }

        needs_reindex = False
        if COLLECTION_NAME in existing_collections:
            self.collection = self.chroma_client.get_collection(COLLECTION_NAME)
            existing_count = self.collection.count()
            existing_model = (self.collection.metadata or {}).get("embedding_model")

            if verbose:
                print(f"   Collection '{COLLECTION_NAME}' already exists", flush=True)

            if existing_count == len(chunks) and existing_model == self.embedding_model_name:
                if verbose:
                    print(f"   Existing index is ready ({existing_count} chunks)", flush=True)
            else:
                if verbose:
                    reason = "embedding model changed" if existing_model != self.embedding_model_name else "size mismatch"
                    print(f"   Rebuilding collection ({reason})...", flush=True)

                self.chroma_client.delete_collection(COLLECTION_NAME)
                needs_reindex = True
        else:
            if verbose:
                print(f"   Creating collection '{COLLECTION_NAME}'...", flush=True)
            needs_reindex = True

        if needs_reindex:
            self.collection = self.chroma_client.create_collection(
                name=COLLECTION_NAME,
                metadata=collection_metadata,
            )

            texts = [chunk.get("text", "") for chunk in chunks]

            if verbose:
                print(f"   Computing embeddings for {len(chunks)} chunks...", flush=True)

            embeddings = self.embeddings_model.encode(
                texts,
                batch_size=self.encode_batch_size,
                show_progress_bar=verbose,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).tolist()

            if verbose:
                print(f"   Adding chunks to ChromaDB in batches of {self.upsert_batch_size}...", flush=True)

            for start in range(0, len(chunks), self.upsert_batch_size):
                end = min(start + self.upsert_batch_size, len(chunks))
                batch_chunks = chunks[start:end]
                self.collection.upsert(
                    ids=[f"chunk_{i}" for i in range(start, end)],
                    embeddings=embeddings[start:end],
                    documents=texts[start:end],
                    metadatas=[
                        {
                            "source": chunk.get("source", "unknown"),
                            "page": chunk.get("page", -1),
                            "chunk_index": chunk.get("chunk_index", i),
                        }
                        for i, chunk in enumerate(batch_chunks, start)
                    ],
                )
                if verbose:
                    print(f"      Upserted {end}/{len(chunks)} chunks", flush=True)

            if verbose:
                print("   Collection created and indexed", flush=True)
        else:
            if self.collection is None:
                self.collection = self.chroma_client.get_collection(COLLECTION_NAME)

        # Build BM25 index
        if verbose:
            print("   Building BM25 sparse index...", flush=True)

        texts = [chunk.get("text", "") for chunk in chunks]
        # Simple tokenization: lowercase and split on whitespace
        self.tokenized_chunks = [text.lower().split() for text in texts]
        self.bm25_index = BM25Okapi(self.tokenized_chunks)

        if verbose:
            print(f"   BM25 index built with {len(chunks)} documents", flush=True)
            print("   Chunk loading complete", flush=True)

        return len(chunks)

    def retrieve_dense(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve top-k relevant chunks using dense (cosine similarity) retrieval."""
        if self.collection is None:
            raise RuntimeError("Collection not loaded. Call load_chunks() first.")

        n_results = top_k or self.dense_top_k
        expanded_query = self._expand_query(query)
        query_embedding = self.embeddings_model.encode(
            expanded_query,
            normalize_embeddings=True,
        ).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        retrieved = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                retrieved.append(
                    {
                        "text": doc,
                        "source": metadata.get("source", "unknown"),
                        "page": metadata.get("page", -1),
                        "distance": results["distances"][0][i],
                        "rank": i + 1,  # For RRF calculation
                    }
                )

        return retrieved

    def retrieve_sparse(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve top-k relevant chunks using sparse (BM25) retrieval."""
        if self.bm25_index is None:
            raise RuntimeError("BM25 index not loaded. Call load_chunks() first.")

        n_results = top_k or self.sparse_top_k
        expanded_query = self._expand_query(query)
        query_tokens = expanded_query.lower().split()
        scores = self.bm25_index.get_scores(query_tokens)

        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_results]

        retrieved = []
        for rank, idx in enumerate(top_indices):
            if idx < len(self.chunks_data):
                chunk = self.chunks_data[idx]
                retrieved.append(
                    {
                        "text": chunk.get("text", ""),
                        "source": chunk.get("source", "unknown"),
                        "page": chunk.get("page", -1),
                        "bm25_score": scores[idx],
                        "rank": rank + 1,  # For RRF calculation
                    }
                )

        return retrieved

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict],
        final_top_k: Optional[int] = None,
    ) -> List[Dict]:
        """Fuse rankings using Reciprocal Rank Fusion (RRF)."""
        # Build RRF scores: RRF(d) = sum over all systems of 1/(k + rank(d))
        rrf_scores = {}
        chunk_map = {}  # Map to store full chunk info

        # Add dense results
        for result in dense_results:
            key = (result["source"], result["page"], result["text"][:50])  # Use text preview as tiebreaker
            rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (self.rrf_k + result["rank"])
            chunk_map[key] = result

        # Add sparse results
        for result in sparse_results:
            key = (result["source"], result["page"], result["text"][:50])
            rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (self.rrf_k + result["rank"])
            if key not in chunk_map:
                chunk_map[key] = result

        # Sort by RRF score and return top final_top_k
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        fused_results = []

        limit = final_top_k or self.final_top_k
        for rank, key in enumerate(sorted_keys[:limit]):
            result = chunk_map[key].copy()
            result["rrf_score"] = rrf_scores[key]
            result["fusion_rank"] = rank + 1
            fused_results.append(result)

        return fused_results

    def retrieve_hybrid(self, query: str, final_top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve using hybrid search: dense + sparse with RRF fusion."""
        dense_results = self.retrieve_dense(query)
        sparse_results = self.retrieve_sparse(query)

        mentioned_companies = self._detect_companies(query)
        if mentioned_companies:
            dense_filtered = self._filter_by_company(dense_results, mentioned_companies)
            sparse_filtered = self._filter_by_company(sparse_results, mentioned_companies)
            if dense_filtered and sparse_filtered:
                dense_results = dense_filtered
                sparse_results = sparse_filtered

        fused_results = self._reciprocal_rank_fusion(
            dense_results,
            sparse_results,
            final_top_k=final_top_k,
        )

        # Rerank only a small preselected pool to avoid over-aggressive reshuffling
        target_k = final_top_k or self.final_top_k
        preselect_k = min(len(fused_results), max(target_k, 5))
        preselected = fused_results[:preselect_k]
        reranked = self._rerank_answer_quality(query, preselected, mentioned_companies)
        return reranked[:target_k]

    @staticmethod
    def _detect_companies(query: str) -> List[str]:
        query_lower = query.lower()
        companies = []
        for company in ("fpt", "vinamilk", "masan"):
            if company in query_lower:
                companies.append(company)
        return companies

    @staticmethod
    def _filter_by_company(results: List[Dict[str, Any]], companies: List[str]) -> List[Dict[str, Any]]:
        filtered = [r for r in results if any(c in r.get("source", "").lower() for c in companies)]
        return filtered

    def _rerank_answer_quality(
        self,
        query: str,
        fused_results: List[Dict[str, Any]],
        companies: List[str],
    ) -> List[Dict[str, Any]]:
        if not fused_results:
            return fused_results

        # Use original query terms for rerank to reduce expansion-driven drift
        query_lower = query.lower()
        keywords = [t for t in query_lower.split() if len(t) > 3]

        def score_chunk(chunk: Dict[str, Any]) -> float:
            text = chunk.get("text", "").lower()
            rrf_score = float(chunk.get("rrf_score", 0.0))
            keyword_hits = sum(1 for kw in keywords if kw in text)
            company_hits = sum(1 for c in companies if c in text)
            length = len(text)
            length_score = max(0.0, 1.0 - abs(length - 500) / 500)
            return rrf_score + (0.03 * keyword_hits) + (0.05 * company_hits) + (0.01 * length_score)

        return sorted(fused_results, key=score_chunk, reverse=True)

    @staticmethod
    def _expand_query(query: str) -> str:
        """Lightweight synonym expansion for Vietnamese query gaps."""
        expansions = {
            "cơ hội": ["opportunity", "growth", "potential"],
            "rủi ro": ["risk", "threat"],
            "chiến lược": ["strategy", "plan"],
            "kế hoạch": ["plan", "roadmap"],
            "tăng trưởng": ["growth"],
        }

        query_lower = query.lower()
        extra_terms = []
        for key, synonyms in expansions.items():
            if key in query_lower:
                extra_terms.extend(synonyms)

        if not extra_terms:
            return query

        return f"{query} {' '.join(extra_terms)}"

    def _has_sufficient_context(self, context_chunks: List[Dict[str, Any]]) -> bool:
        """Check if retrieved context is sufficient for reliable generation."""
        if not context_chunks:
            return False

        # For V2 hybrid search, check RRF scores for meaningful fusion signals
        if context_chunks and "rrf_score" in context_chunks[0]:
            # Require a stronger fusion signal to avoid hallucination
            best_rrf_score = context_chunks[0].get("rrf_score", 0)
            has_sufficient_length = any(len(chunk.get("text", "")) >= 200 for chunk in context_chunks)
            return best_rrf_score >= 0.02 and has_sufficient_length
        
        # Fallback to distance-based threshold for dense-only
        if context_chunks and "distance" in context_chunks[0]:
            best_distance = min(chunk["distance"] for chunk in context_chunks)
            # Stricter threshold: require very good semantic match
            return best_distance <= (self.relevance_distance_threshold - 0.15)

        return False

    @staticmethod
    def _normalize_source_name(source: str) -> str:
        return Path(source).name if source else "unknown"

    def _format_citations(self, context_chunks: List[Dict[str, Any]]) -> List[str]:
        citations = {
            f"[{self._normalize_source_name(chunk['source'])} - Page {chunk['page']}]"
            for chunk in context_chunks
        }
        return sorted(citations)

    def _select_generation_chunks(self, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep the strongest unique chunks small enough for local LLM."""
        selected = []
        seen = set()

        for chunk in context_chunks:
            key = (chunk.get("source"), chunk.get("page"), chunk.get("text"))
            if key in seen:
                continue
            seen.add(key)

            # Measure text length
            text_len = len(chunk.get("text", ""))
            if text_len > self.max_context_chars_per_chunk:
                # Truncate intelligently: take first N chars, then backtrack to end of sentence
                truncated = chunk["text"][: self.max_context_chars_per_chunk]
                last_period = truncated.rfind(".")
                if last_period > 0:
                    truncated = truncated[: last_period + 1]
                chunk = {**chunk, "text": truncated}

            selected.append(chunk)

            if len(selected) >= self.max_generation_chunks:
                break

        return selected

    def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]], language: str = "en") -> str:
        """Generate answer using Ollama qwen2.5:3b with retrieved context."""
        if not self._has_sufficient_context(context_chunks):
            return NOT_FOUND_MESSAGES.get(language, NOT_FOUND_MESSAGES["en"])

        generation_chunks = self._select_generation_chunks(context_chunks)
        context_text = "\n\n".join(
            [f"[{self._normalize_source_name(chunk['source'])} - Page {chunk['page']}]\n{chunk['text']}" for chunk in generation_chunks]
        )

        citations = self._format_citations(generation_chunks)

        if language == "vi":
            system_prompt = """Bạn là trợ lý Q&A thông minh cho hệ thống doanh nghiệp. Sử dụng bối cảnh được cung cấp để trả lời câu hỏi. 
Nếu không tìm thấy thông tin, hãy trả lời rõ ràng rằng bạn không thể tìm thấy câu trả lời.
Trích dẫn nguồn tài liệu khi có thể."""
            user_prompt = f"""Bối cảnh:
{context_text}

Câu hỏi: {query}

Trả lời dựa trên bối cảnh ở trên."""
        else:
            system_prompt = """You are an intelligent Q&A assistant for an enterprise system. Use the provided context to answer the question.
If you cannot find the information, clearly state that you cannot provide an answer based on the given context.
Cite document sources when possible."""
            user_prompt = f"""Context:
{context_text}

Question: {query}

Answer based on the context above."""

        # Retry logic with exponential backoff for timeout resilience
        max_retries = 2
        retry_delay = 2  # seconds
        answer = None
        
        for attempt in range(max_retries + 1):
            try:
                # Combine system and user prompt into single input
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                answer = self.llm.invoke(full_prompt)
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < max_retries:
                    print(f"LLM timeout attempt {attempt + 1}/{max_retries + 1}, retrying in {retry_delay}s...", flush=True)
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"LLM timeout after {max_retries + 1} attempts: {e}", flush=True)
                    answer = NOT_FOUND_MESSAGES.get(language, NOT_FOUND_MESSAGES["en"])
        
        if answer is None:
            answer = NOT_FOUND_MESSAGES.get(language, NOT_FOUND_MESSAGES["en"])

        # Append citations
        if citations:
            answer += f"\n\n**Sources:** {', '.join(citations)}"

        return answer

    def answer(self, query: str, language: Optional[str] = None) -> str:
        """Full pipeline: retrieve (hybrid) + generate answer."""
        if language is None:
            language = detect_language(query)

        context_chunks = self.retrieve_hybrid(query)
        answer = self.generate_answer(query, context_chunks, language)

        return answer

    def answer_with_context(self, query: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Full pipeline with context tracking for evaluation."""
        if language is None:
            language = detect_language(query)

        context_chunks = self.retrieve_hybrid(query)
        answer = self.generate_answer(query, context_chunks, language)

        return {
            "query": query,
            "language": language,
            "answer": answer,
            "retrieved_chunks": context_chunks,
            "num_chunks": len(context_chunks),
        }
