"""Re-index ChromaDB with multilingual model in a new collection.

This script creates a new ChromaDB collection "querionyx_v1_multilingual" as a duplicate
of "querionyx_v1", keeping the original as baseline for comparison.

Purpose:
- Maintain baseline collection (querionyx_v1) for V1 vs V2 comparison
- Create multilingual collection (querionyx_v1_multilingual) for new indices
- Support easy rollback if needed
"""

import os
import pickle
import sys
from pathlib import Path
from typing import Optional

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "chunks_recursive.pkl"
CHROMA_DB_PATH = PROJECT_ROOT / "data" / "chroma_db"
EMBEDDING_CACHE_DIR = PROJECT_ROOT / "data" / "models" / "sentence_transformers"

BASELINE_COLLECTION_NAME = "querionyx_v1"
MULTILINGUAL_COLLECTION_NAME = "querionyx_v1_multilingual"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def load_chunks(verbose: bool = True) -> list:
    """Load preprocessed chunks from pickle."""
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(f"Chunks file not found: {CHUNKS_FILE}")

    if verbose:
        print(f"Loading chunks from {CHUNKS_FILE}...", flush=True)

    with open(CHUNKS_FILE, "rb") as f:
        chunks = pickle.load(f)

    if verbose:
        print(f"   Loaded {len(chunks)} chunks", flush=True)

    return chunks


def reindex_chromadb(
    baseline_collection_name: str = BASELINE_COLLECTION_NAME,
    multilingual_collection_name: str = MULTILINGUAL_COLLECTION_NAME,
    embedding_model_name: str = EMBEDDING_MODEL,
    upsert_batch_size: int = 1000,
    encode_batch_size: int = 64,
    verbose: bool = True,
) -> dict:
    """
    Re-index ChromaDB with multilingual collection.

    Strategy:
    1. Load existing baseline collection embeddings (if available)
    2. If not available, compute embeddings from scratch
    3. Create new multilingual collection with same embeddings
    """
    if verbose:
        print("=" * 80)
        print("ChromaDB Re-indexing: Create Multilingual Collection")
        print("=" * 80)

    # Load chunks
    if verbose:
        print("\n[1/5] Loading chunks...", flush=True)
    chunks = load_chunks(verbose=verbose)
    num_chunks = len(chunks)

    # Initialize ChromaDB
    if verbose:
        print("\n[2/5] Initializing ChromaDB...", flush=True)
    CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    if verbose:
        print(f"   ChromaDB initialized at {CHROMA_DB_PATH}")

    # Check if multilingual collection already exists
    existing_collections = {col.name for col in chroma_client.list_collections()}

    if multilingual_collection_name in existing_collections:
        if verbose:
            print(f"\n   Collection '{multilingual_collection_name}' already exists")
        multilingual_col = chroma_client.get_collection(multilingual_collection_name)
        existing_count = multilingual_col.count()
        if verbose:
            print(f"   Existing collection has {existing_count} chunks")
        if existing_count == num_chunks:
            if verbose:
                print("   ✓ Collection is up-to-date; no re-indexing needed")
            return {
                "status": "already_indexed",
                "collection": multilingual_collection_name,
                "chunks": num_chunks,
            }
        else:
            if verbose:
                print(f"   Deleting outdated collection ({existing_count} vs {num_chunks} chunks)...")
            chroma_client.delete_collection(multilingual_collection_name)

    # Load or compute embeddings
    if verbose:
        print("\n[3/5] Loading embeddings model...", flush=True)
    EMBEDDING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    embeddings_model = SentenceTransformer(
        embedding_model_name,
        cache_folder=str(EMBEDDING_CACHE_DIR),
    )
    if verbose:
        print(f"   Model loaded: {embedding_model_name}")

    # Check if baseline has embeddings we can reuse
    embeddings = None
    if baseline_collection_name in existing_collections:
        if verbose:
            print(f"\n[3.5/5] Attempting to reuse embeddings from '{baseline_collection_name}'...", flush=True)
        try:
            baseline_col = chroma_client.get_collection(baseline_collection_name)
            baseline_count = baseline_col.count()
            baseline_model = (baseline_col.metadata or {}).get("embedding_model")

            if baseline_count == num_chunks and baseline_model == embedding_model_name:
                if verbose:
                    print(f"   ✓ Baseline collection exists with same embeddings")
                    print(f"   Copying {num_chunks} embeddings from baseline...")
                # We'll still need to extract and re-add to new collection
                # ChromaDB doesn't have direct collection copy, so we proceed with full re-index
                if verbose:
                    print("   (Full re-indexing required; ChromaDB has no direct copy)")
            else:
                if verbose:
                    reason = (
                        f"embedding model mismatch ({baseline_model} vs {embedding_model_name})"
                        if baseline_model != embedding_model_name
                        else f"size mismatch ({baseline_count} vs {num_chunks})"
                    )
                    print(f"   ✗ Cannot reuse: {reason}")
        except Exception as e:
            if verbose:
                print(f"   ✗ Error accessing baseline: {e}")

    # Compute embeddings
    if verbose:
        print("\n[4/5] Computing embeddings for multilingual collection...", flush=True)

    texts = [chunk.get("text", "") for chunk in chunks]
    embeddings = embeddings_model.encode(
        texts,
        batch_size=encode_batch_size,
        show_progress_bar=verbose,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).tolist()

    if verbose:
        print(f"   Computed {len(embeddings)} embeddings")

    # Create multilingual collection
    if verbose:
        print("\n[4.5/5] Creating multilingual collection...", flush=True)

    collection_metadata = {
        "hnsw:space": "cosine",
        "embedding_model": embedding_model_name,
        "chunks_file": str(CHUNKS_FILE.relative_to(PROJECT_ROOT)),
        "collection_type": "multilingual",
        "baseline_collection": baseline_collection_name,
    }

    multilingual_col = chroma_client.create_collection(
        name=multilingual_collection_name,
        metadata=collection_metadata,
    )
    if verbose:
        print(f"   Collection created: {multilingual_collection_name}")

    # Upsert chunks
    if verbose:
        print(f"\n[5/5] Indexing {num_chunks} chunks in batches of {upsert_batch_size}...", flush=True)

    for start in range(0, num_chunks, upsert_batch_size):
        end = min(start + upsert_batch_size, num_chunks)
        batch_chunks = chunks[start:end]

        multilingual_col.upsert(
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
            print(f"   Upserted {end}/{num_chunks} chunks", flush=True)

    if verbose:
        print(f"\n✓ Re-indexing complete!")
        print(f"   Collection: {multilingual_collection_name}")
        print(f"   Chunks: {num_chunks}")
        print(f"   Embedding Model: {embedding_model_name}")

    return {
        "status": "reindexed",
        "collection": multilingual_collection_name,
        "chunks": num_chunks,
        "embedding_model": embedding_model_name,
    }


def verify_collections(verbose: bool = True) -> dict:
    """Verify both collections exist and have correct sizes."""
    if verbose:
        print("\n" + "=" * 80)
        print("Verifying Collections")
        print("=" * 80)

    CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

    existing_collections = {col.name: col for col in chroma_client.list_collections()}

    results = {}
    for col_name in [BASELINE_COLLECTION_NAME, MULTILINGUAL_COLLECTION_NAME]:
        if col_name in existing_collections:
            col = existing_collections[col_name]
            count = col.count()
            metadata = col.metadata or {}
            results[col_name] = {
                "exists": True,
                "count": count,
                "embedding_model": metadata.get("embedding_model", "unknown"),
                "collection_type": metadata.get("collection_type", "baseline"),
            }
            if verbose:
                print(f"\n✓ {col_name}")
                print(f"   Count: {count}")
                print(f"   Model: {metadata.get('embedding_model', 'unknown')}")
                print(f"   Type: {metadata.get('collection_type', 'baseline')}")
        else:
            results[col_name] = {"exists": False}
            if verbose:
                print(f"\n✗ {col_name} (not found)")

    return results


def main():
    try:
        # Perform re-indexing
        result = reindex_chromadb(verbose=True)
        print(f"\nResult: {result}")

        # Verify collections
        verification = verify_collections(verbose=True)
        print(f"\nVerification: {verification}")

        print("\n" + "=" * 80)
        print("Success! Collections ready for comparison")
        print("=" * 80)
        print(f"\nBaseline Collection:     {BASELINE_COLLECTION_NAME}")
        print(f"Multilingual Collection: {MULTILINGUAL_COLLECTION_NAME}")
        print("\nYou can now use both collections for V1 vs V2 comparison studies.")

    except Exception as e:
        print(f"\n✗ Error: {e}", flush=True)
        raise


if __name__ == "__main__":
    main()
