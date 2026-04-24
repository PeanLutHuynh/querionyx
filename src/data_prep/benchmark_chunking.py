from __future__ import annotations

import argparse
import pickle
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

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


def chunk_semantic(texts: list[str]) -> list[str]:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    semantic_splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=85,
    )
    documents = semantic_splitter.create_documents(texts)
    return [document.page_content for document in documents if document.page_content and document.page_content.strip()]


def summarize_strategy(name: str, chunks: list[str]) -> StrategyResult:
    token_counts = [len(chunk.split()) for chunk in chunks]
    return StrategyResult(
        name=name,
        total_chunks=len(chunks),
        avg_tokens_per_chunk=mean(token_counts) if token_counts else 0.0,
        min_tokens=min(token_counts) if token_counts else 0,
        max_tokens=max(token_counts) if token_counts else 0,
        sample_chunks=chunks[:3],
    )


def build_markdown(results: list[StrategyResult], sample_files: list[Path]) -> str:
    lines: list[str] = []
    lines.append("# Chunking Benchmark Notes")
    lines.append("")
    lines.append("## Benchmark Setup")
    lines.append("")
    lines.append("- Sample files:")
    for sample_file in sample_files:
        lines.append(f"  - {sample_file.name}")
    lines.append("")
    lines.append("## Comparison Table")
    lines.append("")
    lines.append("| Strategy | Total Chunks | Avg Tokens/Chunk | Min Tokens | Max Tokens |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for result in results:
        lines.append(
            f"| {result.name} | {result.total_chunks} | {result.avg_tokens_per_chunk:.2f} | {result.min_tokens} | {result.max_tokens} |"
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

    sample_files = pdf_paths[: args.sample_count]
    documents = load_documents(sample_files)
    texts = documents_to_texts(documents)
    if not texts:
        print("No text extracted from sample PDFs.")
        return 1

    fixed_chunks = chunk_fixed_size(texts)
    recursive_chunks = chunk_recursive(texts)
    semantic_chunks = chunk_semantic(texts)
    semantic_result = summarize_strategy("Semantic Chunking", semantic_chunks)

    results = [
        summarize_strategy("Fixed-size", fixed_chunks),
        summarize_strategy("Recursive Splitting", recursive_chunks),
        semantic_result,
    ]

    for result in results:
        print(
            f"{result.name}: total={result.total_chunks}, avg_tokens={result.avg_tokens_per_chunk:.2f}, min={result.min_tokens}, max={result.max_tokens}"
        )
        for index, chunk in enumerate(result.sample_chunks, start=1):
            print(f"--- {result.name} sample {index} ---")
            print(chunk[:400])

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(build_markdown(results, sample_files), encoding="utf-8")
    print(f"Benchmark report written to {args.output_md}")

    chunk_count = process_full_corpus(args.input_dir, args.output_pkl)
    print(f"Recursive chunks saved to {args.output_pkl} (total: {chunk_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())