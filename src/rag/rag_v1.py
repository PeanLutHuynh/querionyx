"""RAG Pipeline V1 Baseline - bilingual offline RAG system for Querionyx.

Architecture:
- Bilingual user support: Vietnamese and English questions
- Embeddings: multilingual sentence-transformers model, cached locally
- Vector Store: ChromaDB persistent collection
- Retrieval: Top-5 cosine similarity
- Generation: Ollama phi3 via LangChain OllamaLLM
- Source Attribution: citation of filename + page number
- Anti-hallucination: fixed Vietnamese not-found response
"""

import os
import pickle
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "chunks_recursive.pkl"
CHROMA_DB_PATH = PROJECT_ROOT / "data" / "chroma_db"
EMBEDDING_CACHE_DIR = PROJECT_ROOT / "data" / "models" / "sentence_transformers"
COLLECTION_NAME = "querionyx_v1"

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_LLM_MODEL = "phi3"
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


class RAGPipelineV1:
    """Offline, bilingual, attribution-aware RAG baseline."""

    def __init__(
        self,
        embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
        llm_model: str = DEFAULT_LLM_MODEL,
        top_k: int = 5,
        ollama_base_url: Optional[str] = None,
        relevance_distance_threshold: float = 0.35,
        upsert_batch_size: int = 1000,
        encode_batch_size: int = 64,
        llm_timeout_seconds: int = 90,
        max_context_chars_per_chunk: int = 650,
        max_generation_chunks: int = 3,
    ):
        self.top_k = top_k
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

        print("Initializing RAG Pipeline V1...")
        print(f"  - Embedding model: {embedding_model_name}", flush=True)
        print(f"  - LLM: {llm_model}", flush=True)
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
            num_ctx=3072,
            sync_client_kwargs={"timeout": llm_timeout_seconds},
        )
        print(f"     Ollama endpoint: {self.ollama_base_url}", flush=True)

        self.collection = None
        self.chunks_data = None

    def load_chunks(self, verbose: bool = True) -> int:
        """Load preprocessed chunks from pickle and index them in ChromaDB."""
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
                return len(chunks)

            if verbose:
                reason = "embedding model changed" if existing_model != self.embedding_model_name else "size mismatch"
                print(f"   Rebuilding collection ({reason})...", flush=True)

            self.chroma_client.delete_collection(COLLECTION_NAME)

        else:
            if verbose:
                print(f"   Creating collection '{COLLECTION_NAME}'...", flush=True)

        self.collection = self.chroma_client.create_collection(
            name=COLLECTION_NAME,
            metadata=collection_metadata,
        )
        needs_reindex = True

        if needs_reindex:
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

        return len(chunks)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve top-k relevant chunks using cosine similarity."""
        if self.collection is None:
            raise RuntimeError("Collection not loaded. Call load_chunks() first.")

        n_results = top_k or self.top_k
        query_embedding = self.embeddings_model.encode(
            query,
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
                    }
                )

        return retrieved

    def _has_sufficient_context(self, context_chunks: List[Dict[str, Any]]) -> bool:
        if not context_chunks:
            return False

        best_distance = min(chunk["distance"] for chunk in context_chunks)
        return best_distance <= self.relevance_distance_threshold

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
        """Keep the strongest unique chunks small enough for local phi3."""
        selected = []
        seen = set()

        for chunk in context_chunks:
            key = (chunk.get("source"), chunk.get("page"), chunk.get("text"))
            if key in seen:
                continue
            seen.add(key)
            selected.append(chunk)
            if len(selected) >= self.max_generation_chunks:
                break

        return selected

    def _is_ollama_available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.ollama_base_url}/api/tags", timeout=3) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError):
            return False
        except Exception:
            return False

    def generate(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        language: Optional[str] = None,
    ) -> str:
        """Generate an answer in the user's language using only retrieved context."""
        context_chunks = self._select_generation_chunks(context_chunks)
        answer_language = language or detect_language(question)
        not_found_message = NOT_FOUND_MESSAGES.get(answer_language, NOT_FOUND_MESSAGE)

        if not self._has_sufficient_context(context_chunks):
            return not_found_message

        language_name = "Vietnamese" if answer_language == "vi" else "English"
        citations = self._format_citations(context_chunks)

        context_parts = []
        for chunk in context_chunks:
            source = self._normalize_source_name(chunk["source"])
            page = chunk["page"]
            text = chunk["text"].strip()
            if len(text) > self.max_context_chars_per_chunk:
                text = f"{text[:self.max_context_chars_per_chunk].rstrip()}..."
            context_parts.append(f"[{source} - Page {page}]\n{text}")

        prompt = f"""You are an enterprise Q&A assistant.

Language: {answer_language}

Rules:
- Answer ONLY in {language_name}, the same language as the question.
- Use ONLY the provided context.
- Do NOT use external knowledge.
- Cite factual claims with [filename - Page X].
- If the context is insufficient, answer exactly: "{not_found_message}"
- Keep the answer concise.

CONTEXT:
{chr(10).join(context_parts)}

QUESTION:
{question}

ANSWER:"""

        try:
            answer = self.llm.invoke(prompt).strip()
        except Exception as exc:
            if answer_language == "en":
                return f"Unable to connect to Ollama at {self.ollama_base_url}: {exc}"
            return f"Không thể kết nối Ollama tại {self.ollama_base_url}: {exc}"

        if not_found_message in answer:
            return not_found_message

        missing_citations = [citation for citation in citations if citation not in answer]
        if missing_citations:
            answer = f"{answer}\n\nSources: {', '.join(citations)}"

        return answer

    def query(self, question: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """Run retrieval and generation for a Vietnamese or English question."""
        language = detect_language(question)
        retrieved = self.retrieve(question, top_k=top_k)
        generation_chunks = self._select_generation_chunks(retrieved)
        answer = self.generate(question, generation_chunks, language=language)

        return {
            "answer": answer,
            "sources": [] if answer in NOT_FOUND_MESSAGES.values() else self._format_citations(generation_chunks),
            "context_chunks": retrieved,
            "language": language,
        }


def main():
    """Run a small bilingual smoke test."""
    print("\n" + "=" * 80)
    print("RAG Pipeline V1 - Bilingual Demo")
    print("=" * 80 + "\n")

    pipeline = RAGPipelineV1()
    num_chunks = pipeline.load_chunks(verbose=True)
    print(f"\nRAG Pipeline ready with {num_chunks} indexed chunks\n", flush=True)

    if not pipeline._is_ollama_available():
        print("  Ollama is not running. Start Ollama locally to enable generation.", flush=True)
        print(f"    Endpoint: {pipeline.ollama_base_url}\n", flush=True)

    sample_questions = [
        "Vinamilk quản trị rủi ro như thế nào?",
        "FPT đề cập chiến lược phát triển nào cho năm 2025?",
        "How does Masan describe business risks?",
    ]

    print("=" * 80)
    print("Running Bilingual Sample Queries")
    print("=" * 80 + "\n")

    for i, question in enumerate(sample_questions, 1):
        print(f"Question {i} ({detect_language(question)}):\n{question}\n", flush=True)
        result = pipeline.query(question, top_k=5)

        print(f"Answer:\n{result['answer']}\n", flush=True)
        print(f"Sources ({len(result['sources'])} found):", flush=True)
        for source in result["sources"]:
            print(f"   - {source}", flush=True)
        print(f"\nContext chunks retrieved: {len(result['context_chunks'])}", flush=True)
        print("-" * 80 + "\n", flush=True)


if __name__ == "__main__":
    main()
