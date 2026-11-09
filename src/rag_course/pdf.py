"""PDF Pipeline: data/invoice.pdf from RAG_2, 500/50 chunks per page, top-3."""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from rag_course.core import PDF_PROMPT, Chunk, Models, SourceError, answer_from

DEFAULT_PDF = Path(__file__).resolve().parents[2] / "data" / "invoice.pdf"


def load_pdf(path: Path) -> list[str]:
    try:
        return [page.extract_text() for page in PdfReader(path).pages]
    except PyPdfError as error:
        raise SourceError(f"not a readable PDF: {path} ({error})") from error


def chunks(path: Path = DEFAULT_PDF) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    found = [
        Chunk(text, f"{path}#page={number}")
        for number, page in enumerate(load_pdf(path), 1)
        for text in splitter.split_text(page)
    ]
    if not found:
        raise SourceError(f"no text found in PDF: {path}")
    return found


def ask(question: str, models: Models, path: Path = DEFAULT_PDF) -> str:
    return answer_from(question, chunks(path), models, PDF_PROMPT, k=3)
