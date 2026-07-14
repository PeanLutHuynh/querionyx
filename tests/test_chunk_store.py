import tempfile
import unittest
from pathlib import Path

from src.runtime.chunk_store import CHUNKS_FILE, load_chunks, save_chunks


class ChunkStoreTests(unittest.TestCase):
    def test_versioned_corpus_is_complete(self):
        chunks = load_chunks()
        self.assertEqual(len(chunks), 9670)
        self.assertEqual(len({chunk["source"] for chunk in chunks}), 9)
        self.assertEqual(CHUNKS_FILE.suffixes[-2:], [".json", ".gz"])

    def test_round_trip_is_deterministic(self):
        chunks = [
            {"source": "sample.pdf", "page": 1, "chunk_index": 0, "text": "Example text."},
            {"source": "sample.pdf", "page": 2, "chunk_index": 0, "text": "Second page."},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chunks.json.gz"
            self.assertEqual(save_chunks(chunks, path), 2)
            first = path.read_bytes()
            self.assertEqual(load_chunks(path), chunks)
            save_chunks(chunks, path)
            self.assertEqual(path.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
