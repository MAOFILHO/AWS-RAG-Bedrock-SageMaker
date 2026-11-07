"""PDF Pipeline: data/invoice.pdf from RAG_2, 500/50 chunks per page, top-3."""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from rag_course.core import PDF_PROMPT, Chunk, Models, answer_from

DEFAULT_PDF = Path(__file__).resolve().parents[2] / "data" / "invoice.pdf"


def load_pdf(path: Path) -> list[str]:
    return [page.extract_text() for page in PdfReader(path).pages]


def ask(question: str, models: Models, path: Path = DEFAULT_PDF) -> str:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = [
        Chunk(text, f"{path}#page={number}")
        for number, page in enumerate(load_pdf(path), 1)
        for text in splitter.split_text(page)
    ]
    return answer_from(question, chunks, models, PDF_PROMPT, k=3)
