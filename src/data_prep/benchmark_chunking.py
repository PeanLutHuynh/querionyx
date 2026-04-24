from __future__ import annotations

import argparse
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_REPORTS_DIR = PROJECT_ROOT / "data" / "raw" / "annual_reports"
NOTES_PATH = PROJECT_ROOT / "docs" / "chunking_notes.md"
PICKLE_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_recursive.pkl"


@dataclass(frozen=True)
class StrategyResult:
    name: str
    total_chunks: int
    avg_tokens_per_chunk: float
    min_tokens: int
    max_tokens: int
    context_precision: float
    sample_chunks: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark chunking strategies for annual report PDFs.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=RAW_REPORTS_DIR,
        help="Directory containing annual report PDFs",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=2,
        help="Number of PDF files used for benchmark",
    )
    parser.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.3,
        help="Cosine distance threshold used for semantic chunking",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=NOTES_PATH,
        help="Output markdown file for benchmark notes",
    )
    parser.add_argument(
        "--output-pkl",
        type=Path,
        default=PICKLE_PATH,
        help="Output pickle path for full corpus recursive chunks",
    )
    return parser.parse_args()


def load_documents(pdf_paths: list[Path]):
    documents = []
    for pdf_path in pdf_paths:
        loader = PyMuPDFLoader(str(pdf_path))
        documents.extend(loader.load())
    return documents


def documents_to_texts(documents) -> list[str]:
    return [document.page_content for document in documents if document.page_content and document.page_content.strip()]


def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", compact) if sentence.strip()]


def chunk_fixed_size(texts: list[str]) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
    chunks: list[str] = []
    for text in texts:
        chunks.extend(splitter.split_text(text))
    return chunks


def chunk_recursive(texts: list[str]) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " "],
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks: list[str] = []
    for text in texts:
        chunks.extend(splitter.split_text(text))
    return chunks


def chunk_semantic(texts: list[str], model: SentenceTransformer, distance_threshold: float) -> list[str]:
    semantic_chunks: list[str] = []
    for text in texts:
        sentences = split_sentences(text)
        if not sentences:
            continue
        if len(sentences) == 1:
            semantic_chunks.append(sentences[0])
            continue

        sentence_vectors = model.encode(sentences, normalize_embeddings=True)
        current_chunk = [sentences[0]]
        for index in range(1, len(sentences)):
            cosine_similarity = float((sentence_vectors[index - 1] * sentence_vectors[index]).sum())
            cosine_distance = 1.0 - cosine_similarity
            if cosine_distance > distance_threshold:
                semantic_chunks.append(" ".join(current_chunk).strip())
                current_chunk = [sentences[index]]
            else:
                current_chunk.append(sentences[index])

        if current_chunk:
            semantic_chunks.append(" ".join(current_chunk).strip())

    return [chunk for chunk in semantic_chunks if chunk]


def build_probe_queries(texts: list[str], limit: int = 10) -> list[str]:
    candidate_sentences: list[str] = []
    for text in texts:
        for sentence in split_sentences(text):
            if len(sentence.split()) >= 10:
                candidate_sentences.append(sentence)
    if not candidate_sentences:
        return []
    step = max(1, len(candidate_sentences) // limit)
    return [candidate_sentences[index] for index in range(0, len(candidate_sentences), step)][:limit]


def compute_context_precision(chunks: list[str], queries: list[str], model: SentenceTransformer) -> float:
    if not chunks or not queries:
        return 0.0

    chunk_vectors = model.encode(chunks, normalize_embeddings=True)
    query_vectors = model.encode(queries, normalize_embeddings=True)

    precise_hits = 0
    for query, query_vector in zip(queries, query_vectors):
        scores = chunk_vectors @ query_vector
        best_index = int(scores.argmax())
        query_tokens = set(re.findall(r"\w+", query.lower()))
        chunk_tokens = set(re.findall(r"\w+", chunks[best_index].lower()))
        if not query_tokens:
            continue
        coverage = len(query_tokens & chunk_tokens) / len(query_tokens)
        if coverage >= 0.6:
            precise_hits += 1

    return (precise_hits / len(queries)) * 100


def summarize_strategy(name: str, chunks: list[str], context_precision: float) -> StrategyResult:
    token_counts = [len(chunk.split()) for chunk in chunks]
    return StrategyResult(
        name=name,
        total_chunks=len(chunks),
        avg_tokens_per_chunk=mean(token_counts) if token_counts else 0.0,
        min_tokens=min(token_counts) if token_counts else 0,
        max_tokens=max(token_counts) if token_counts else 0,
        context_precision=context_precision,
        sample_chunks=chunks[:3],
    )


def build_markdown(results: list[StrategyResult], sample_files: list[Path], semantic_threshold: float) -> str:
    lines: list[str] = []
    lines.append("# Chunking Benchmark Notes")
    lines.append("")
    lines.append("## Benchmark Setup")
    lines.append("")
    lines.append("- Sample files:")
    for sample_file in sample_files:
        lines.append(f"  - {sample_file.name}")
    lines.append(f"- Semantic chunking cosine distance threshold: {semantic_threshold}")
    lines.append("- Preliminary Context Precision: retrieval hit-rate on 10 probe queries")
    lines.append("")
    lines.append("## Comparison Table")
    lines.append("")
    lines.append("| Strategy | Total Chunks | Avg Tokens/Chunk | Min Tokens | Max Tokens | Context Precision (%) |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for result in results:
        lines.append(
            f"| {result.name} | {result.total_chunks} | {result.avg_tokens_per_chunk:.2f} | {result.min_tokens} | {result.max_tokens} | {result.context_precision:.2f} |"
        )

    lines.append("")
    lines.append("## Sample Chunks")
    lines.append("")
    for result in results:
        lines.append(f"### {result.name}")
        lines.append("")
        if not result.sample_chunks:
            lines.append("No chunks generated.")
            lines.append("")
            continue
        for index, chunk in enumerate(result.sample_chunks, start=1):
            lines.append(f"#### Chunk {index}")
            lines.append("")
            lines.append("```")
            lines.append(chunk[:1200])
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def process_full_corpus(input_dir: Path, output_pickle: Path) -> int:
    pdf_paths = sorted(input_dir.glob("*.pdf"))
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " "],
        chunk_size=500,
        chunk_overlap=50,
    )

    all_chunks: list[dict] = []
    for pdf_path in pdf_paths:
        loader = PyMuPDFLoader(str(pdf_path))
        documents = loader.load()
        for document in documents:
            page_text = (document.page_content or "").strip()
            if not page_text:
                continue
            page_chunks = splitter.split_text(page_text)
            for chunk_index, chunk_text in enumerate(page_chunks):
                all_chunks.append(
                    {
                        "source": pdf_path.name,
                        "page": document.metadata.get("page"),
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                    }
                )

    output_pickle.parent.mkdir(parents=True, exist_ok=True)
    with output_pickle.open("wb") as file:
        pickle.dump(all_chunks, file)
    return len(all_chunks)


def select_sample_files(pdf_paths: list[Path], sample_count: int) -> list[Path]:
    fpt_file = next((path for path in pdf_paths if path.name.lower().startswith("fpt_")), None)
    vinamilk_file = next((path for path in pdf_paths if path.name.lower().startswith("vinamilk_")), None)
    selected: list[Path] = []
    if fpt_file:
        selected.append(fpt_file)
    if vinamilk_file and vinamilk_file not in selected:
        selected.append(vinamilk_file)
    if len(selected) < sample_count:
        for path in pdf_paths:
            if path not in selected:
                selected.append(path)
            if len(selected) == sample_count:
                break
    return selected[:sample_count]


def main() -> int:
    load_dotenv(override=True)
    args = parse_args()

    if not args.input_dir.exists():
        print(f"Input folder does not exist: {args.input_dir}")
        return 1

    pdf_paths = sorted(args.input_dir.glob("*.pdf"))
    if len(pdf_paths) < args.sample_count:
        print(f"Need at least {args.sample_count} PDF files, found {len(pdf_paths)}")
        return 1

    sample_files = select_sample_files(pdf_paths, args.sample_count)
    documents = load_documents(sample_files)
    texts = documents_to_texts(documents)
    if not texts:
        print("No text extracted from sample PDFs.")
        return 1

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    probe_queries = build_probe_queries(texts, limit=10)

    fixed_chunks = chunk_fixed_size(texts)
    recursive_chunks = chunk_recursive(texts)
    semantic_chunks = chunk_semantic(texts, model=model, distance_threshold=args.semantic_threshold)

    results = [
        summarize_strategy("Fixed-size", fixed_chunks, compute_context_precision(fixed_chunks, probe_queries, model)),
        summarize_strategy(
            "Recursive Splitting",
            recursive_chunks,
            compute_context_precision(recursive_chunks, probe_queries, model),
        ),
        summarize_strategy(
            "Semantic Chunking",
            semantic_chunks,
            compute_context_precision(semantic_chunks, probe_queries, model),
        ),
    ]

    for result in results:
        print(
            f"{result.name}: total={result.total_chunks}, avg_tokens={result.avg_tokens_per_chunk:.2f}, min={result.min_tokens}, max={result.max_tokens}, context_precision={result.context_precision:.2f}%"
        )
        for index, chunk in enumerate(result.sample_chunks, start=1):
            print(f"--- {result.name} sample {index} ---")
            print(chunk[:400])

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(results, sample_files, args.semantic_threshold), encoding="utf-8")
    print(f"Benchmark report written to {args.output_md}")

    chunk_count = process_full_corpus(args.input_dir, args.output_pkl)
    print(f"Recursive chunks saved to {args.output_pkl} (total: {chunk_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())