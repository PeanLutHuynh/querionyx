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
    note: str


def inspect_pdf(pdf_path: Path) -> PdfInspectionResult:
    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        first_page_text = document.load_page(0).get_text("text").strip() if page_count else ""
        char_count = len(first_page_text)
        has_text_layer = char_count > 100
        note = "OK" if has_text_layer else "Cần OCR"

    return PdfInspectionResult(
        file_name=pdf_path.name,
        page_count=page_count,
        first_page_char_count=char_count,
        has_text_layer=has_text_layer,
        note=note,
    )


def build_markdown(results: list[PdfInspectionResult], source_dir: Path) -> str:
    lines: list[str] = []
    lines.append("# PDF Inspection Report")
    lines.append("")
    lines.append(f"Source folder: `{source_dir}`")
    lines.append("")
    lines.append("| File | Pages | First Page Characters | Text Layer | Note |")
    lines.append("| --- | ---: | ---: | --- | --- |")

    for result in results:
        text_layer_label = "Yes" if result.has_text_layer else "No"
        lines.append(
            f"| {result.file_name} | {result.page_count} | {result.first_page_char_count} | {text_layer_label} | {result.note} |"
        )

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total PDF files: {len(results)}")
    lines.append(f"- Files with text layer: {sum(1 for result in results if result.has_text_layer)}")
    lines.append(f"- Files needing OCR: {sum(1 for result in results if not result.has_text_layer)}")
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
            f"{result.file_name} | pages={result.page_count} | first_page_chars={result.first_page_char_count} | text_layer={result.has_text_layer} | {result.note}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown(results, input_dir), encoding="utf-8")
    print(f"Report written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())