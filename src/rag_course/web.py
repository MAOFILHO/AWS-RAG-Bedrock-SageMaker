"""Web Pipeline: the two IBM pages from RAG_1, 500/50 chunks, top-3."""

from typing import Callable

import requests
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_course.core import WEB_PROMPT, Chunk, Models, VectorStore, answer_with_context, store_from

URLS = (
    "https://www.ibm.com/think/topics/cloud-computing",
    "https://www.ibm.com/think/topics/data-science",
)


def html_to_text(html: str) -> str:
    lines = (" ".join(line.split()) for line in BeautifulSoup(html, "html.parser").get_text().splitlines())
    return "\n".join(line for line in lines if line)


def fetch_page(url: str) -> str:
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 rag-course"})
    response.raise_for_status()
    return html_to_text(response.text)


def chunks(fetch: Callable[[str], str] = fetch_page) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return [Chunk(text, url) for url in URLS for text in splitter.split_text(fetch(url))]


def store(models: Models, fetch: Callable[[str], str] = fetch_page) -> VectorStore:
    return store_from(models, chunks(fetch))


def answer(question: str, source: VectorStore, models: Models) -> str:
    return answer_with_context(question, source, models, WEB_PROMPT, k=3)[0]


def ask(question: str, models: Models, fetch: Callable[[str], str] = fetch_page) -> str:
    return answer(question, store(models, fetch), models)
