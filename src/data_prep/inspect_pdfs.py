from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import fitz
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "annual_reports"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "docs" / "pdf_inspection.md"


@dataclass(frozen=True)
class PdfInspectionResult:
    file_name: str
    page_count: int
    first_page_char_count: int
    has_text_layer: bool
    sampled_pages: int
    avg_sample_chars: int
    extraction_quality: str
    ocr_recommended: bool
    note: str


def inspect_pdf(pdf_path: Path) -> PdfInspectionResult:
    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        first_page_text = document.load_page(0).get_text("text").strip() if page_count else ""
        first_page_char_count = len(first_page_text)

        sample_indexes = sorted(
            {
                index
                for index in [0, 1, 2, max(page_count // 2, 0), max(page_count - 1, 0)]
                if 0 <= index < page_count
            }
        )
        sample_texts = [document.load_page(index).get_text("text") for index in sample_indexes]
        sample_lengths = [len((text or "").strip()) for text in sample_texts]

        has_text_layer = any(length > 100 for length in sample_lengths) or first_page_char_count > 100

        merged_text = " ".join(" ".join((text or "").split()) for text in sample_texts).strip()
        if merged_text:
            alpha_ratio = sum(character.isalpha() for character in merged_text) / len(merged_text)
            tokens = merged_text.split()
            single_char_ratio = (sum(len(token) == 1 for token in tokens) / len(tokens)) if tokens else 1.0
        else:
            alpha_ratio = 0.0
            single_char_ratio = 1.0

        if not has_text_layer:
            extraction_quality = "No text layer"
            ocr_recommended = True
            note = "Cần OCR"
        elif alpha_ratio < 0.45 or single_char_ratio > 0.35:
            extraction_quality = "Text layer but noisy"
            ocr_recommended = True
            note = "OCR recommended"
        else:
            extraction_quality = "Digital text"
            ocr_recommended = False
            note = "OK"

    return PdfInspectionResult(
        file_name=pdf_path.name,
        page_count=page_count,
        first_page_char_count=first_page_char_count,
        has_text_layer=has_text_layer,
        sampled_pages=len(sample_indexes),
        avg_sample_chars=(sum(sample_lengths) // len(sample_lengths)) if sample_lengths else 0,
        extraction_quality=extraction_quality,
        ocr_recommended=ocr_recommended,
        note=note,
    )


def build_markdown(results: list[PdfInspectionResult], source_dir: Path) -> str:
    lines: list[str] = []
    lines.append("# PDF Inspection Report")
    lines.append("")
    lines.append(f"Source folder: `{source_dir}`")
    lines.append("")
    lines.append("| File | Pages | First Page Characters | Text Layer | Sampled Pages | Avg Sample Characters | Extraction Quality | OCR Recommended | Note |")
    lines.append("| --- | ---: | ---: | --- | ---: | ---: | --- | --- | --- |")

    for result in results:
        text_layer_label = "Yes" if result.has_text_layer else "No"
        ocr_label = "Yes" if result.ocr_recommended else "No"
        lines.append(
            f"| {result.file_name} | {result.page_count} | {result.first_page_char_count} | {text_layer_label} | {result.sampled_pages} | {result.avg_sample_chars} | {result.extraction_quality} | {ocr_label} | {result.note} |"
        )

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total PDF files: {len(results)}")
    lines.append(f"- Files with text layer: {sum(1 for result in results if result.has_text_layer)}")
    lines.append(f"- Files with digital text quality: {sum(1 for result in results if result.extraction_quality == 'Digital text')}")
    lines.append(f"- Files with noisy text layer: {sum(1 for result in results if result.extraction_quality == 'Text layer but noisy')}")
    lines.append(f"- Files needing OCR (no text layer): {sum(1 for result in results if result.extraction_quality == 'No text layer')}")
    lines.append(f"- Files with OCR recommended: {sum(1 for result in results if result.ocr_recommended)}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect annual report PDFs for text layer presence.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR, help="Folder containing PDF files")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_PATH, help="Markdown report output path")
    return parser.parse_args()


def main() -> int:
    load_dotenv(override=True)
    args = parse_args()

    input_dir = args.input_dir
    output_path = args.output_md

    if not input_dir.exists():
        print(f"Input folder does not exist: {input_dir}")
        return 1

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in: {input_dir}")
        return 1

    results = [inspect_pdf(pdf_path) for pdf_path in pdf_files]

    for result in results:
        print(
            f"{result.file_name} | pages={result.page_count} | first_page_chars={result.first_page_char_count} | text_layer={result.has_text_layer} | quality={result.extraction_quality} | ocr_recommended={result.ocr_recommended} | {result.note}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown(results, input_dir), encoding="utf-8")
    print(f"Report written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())