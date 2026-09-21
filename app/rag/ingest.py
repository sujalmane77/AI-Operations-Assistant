"""
Ingests data/documents/company_handbook.pdf into a persistent ChromaDB
collection. Chunks by paragraph/heading where possible so section
boundaries stay coherent (important since the whole RAG demo rests on
one document with multiple distinct sections).
"""
import os
import re

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_IMPL", "none")

import chromadb
from chromadb.config import Settings
import pdfplumber

from app.config import config

CHROMA_DIR = config.chroma_db
DOCUMENTS_DIR = config.documents_dir
CHROMA_COLLECTION = config.chroma_collection
from app.rag.embeddings import embed_texts

HEADING_RE = re.compile(r"^\s*#{1,3}\s+(.*)$")  # matches "## Leave Policy" style headings
# Matches top-level numbered headings like "2. Company Snapshot (Fact Sheet)" but not
# table-of-contents lines ("2. Company Snapshot (Fact Sheet) 5") which end in a page number,
# and not sub-numbered headings like "3.1 Names and how they relate".
NUMBERED_HEADING_RE = re.compile(r"^(\d{1,2})\.\s+([A-Za-z(].{2,78})$")
TRAILING_PAGENUM_RE = re.compile(r"\s\d{1,3}$")
CHUNK_SIZE_CHARS = 1800   # ~ 400-500 tokens
CHUNK_OVERLAP_CHARS = 200


def extract_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def split_into_sections(full_text: str) -> list[tuple[str, str]]:
    """
    Returns a list of (section_heading, section_text). If the PDF has no
    markdown-style headings (## Heading), falls back to a single
    "General" section so ingestion still works on plain PDFs.
    """
    lines = full_text.split("\n")
    sections: list[tuple[str, list[str]]] = []
    current_heading = "General"
    current_lines: list[str] = []

    has_markdown_headings = any(HEADING_RE.match(l) for l in lines)
    has_numbered_headings = not has_markdown_headings and any(
        NUMBERED_HEADING_RE.match(l.strip()) and not TRAILING_PAGENUM_RE.search(l.strip())
        for l in lines
    )

    for line in lines:
        stripped = line.strip()
        md_match = HEADING_RE.match(line)
        num_match = NUMBERED_HEADING_RE.match(stripped) if has_numbered_headings else None
        is_heading = False
        heading_text = None

        if has_markdown_headings and md_match:
            is_heading = True
            heading_text = md_match.group(1).strip()
        elif has_numbered_headings and num_match and not TRAILING_PAGENUM_RE.search(stripped):
            is_heading = True
            heading_text = stripped
        elif not has_markdown_headings and not has_numbered_headings and line.strip() and len(line.strip()) < 60 and line.strip() == line.strip().upper() and any(c.isalpha() for c in line):
            is_heading = True
            heading_text = line.strip().title()

        if is_heading:
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = heading_text
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    return [(h, "\n".join(lines).strip()) for h, lines in sections if "\n".join(lines).strip()]


def chunk_text(text: str, size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def ingest(pdf_filename: str = "company_handbook.pdf"):
    pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"Expected company PDF at {pdf_path}. Add your company_handbook.pdf "
            f"to {DOCUMENTS_DIR}/ before running ingestion."
        )

    full_text = extract_text(pdf_path)
    sections = split_into_sections(full_text)

    all_chunks: list[str] = []
    all_metadatas: list[dict] = []
    all_ids: list[str] = []

    chunk_counter = 0
    for heading, section_text in sections:
        for piece in chunk_text(section_text):
            piece = piece.strip()
            if not piece:
                continue
            all_chunks.append(piece)
            all_metadatas.append({"source_section": heading, "source_file": pdf_filename})
            all_ids.append(f"chunk_{chunk_counter}")
            chunk_counter += 1

    if not all_chunks:
        raise ValueError("No text extracted from PDF — is it a scanned/image-only PDF?")

    embeddings = embed_texts(all_chunks)

    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    # Fresh collection each ingest run to avoid stale duplicate chunks.
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(CHROMA_COLLECTION)

    collection.add(
        ids=all_ids,
        embeddings=embeddings,
        documents=all_chunks,
        metadatas=all_metadatas,
    )

    print(f"Ingested {len(all_chunks)} chunks across {len(sections)} sections into '{CHROMA_COLLECTION}'.")
    print("Sections found:", [h for h, _ in sections])
    return len(all_chunks)


if __name__ == "__main__":
    ingest()
