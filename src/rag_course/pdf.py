"""PDF Pipeline: data/k21.pdf from RAG_2, 500/50 chunks per page, top-3."""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from rag_course.core import PDF_PROMPT, Chunk, Models, VectorStore, answer_with_context

DEFAULT_PDF = Path(__file__).resolve().parents[2] / "data" / "k21.pdf"


def load_pdf(path: Path) -> list[str]:
    return [page.extract_text() for page in PdfReader(path).pages]


def chunks(path: Path = DEFAULT_PDF) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return [
        Chunk(text, f"{path}#page={number}")
        for number, page in enumerate(load_pdf(path), 1)
        for text in splitter.split_text(page)
    ]


def store(models: Models, path: Path = DEFAULT_PDF) -> VectorStore:
    return VectorStore(models.embed, chunks(path))


def answer(question: str, source: VectorStore, models: Models) -> str:
    return answer_with_context(question, source, models, PDF_PROMPT, k=3)[0]


def ask(question: str, models: Models, path: Path = DEFAULT_PDF) -> str:
    return answer(question, store(models, path), models)
