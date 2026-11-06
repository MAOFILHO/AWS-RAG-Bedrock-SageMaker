"""Fake Bedrock answer and embedding models, and the saved web pages, for Offline tests."""

import gzip
import re
import zlib
from pathlib import Path

from rag_course.core import DONT_KNOW, Models

WEB_PAGES = Path(__file__).parent / "data" / "web"
STOPWORDS = {"what", "which", "who", "how", "why", "the", "is", "are", "of", "a", "an", "in", "does", "do", "did"}


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS


class FakeEmbeddings:
    """Hashed bag of words: texts that share words get similar vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * 256
            for word in re.findall(r"[a-z0-9]+", text.lower()):
                vector[zlib.crc32(word.encode()) % 256] += 1.0
            vectors.append(vector)
        return vectors


class FakeAnswerModel:
    """Answers with the longest context line holding every question word, else the fixed sentence."""

    def answer(self, prompt: str) -> str:
        assert DONT_KNOW in prompt, "prompt must carry the fixed I-don't-know sentence"
        context = prompt.split("Context:\n", 1)[1].split("\n\nQuestion: ", 1)[0]
        question = prompt.split("\n\nQuestion: ", 1)[1].split("\n\nAnswer:", 1)[0]
        wanted = words(question)
        lines = [line for line in context.splitlines() if wanted and wanted <= words(line)]
        return max(lines, key=len) if lines else DONT_KNOW


def fake_models() -> Models:
    return Models(answer=FakeAnswerModel(), embed=FakeEmbeddings())


def saved_page(url: str) -> str:
    return gzip.decompress((WEB_PAGES / f"{url.rstrip('/').rsplit('/', 1)[-1]}.txt.gz").read_bytes()).decode()


class FakeSqlModel:
    """Writes the SQL scripted for each question, then answers with the result rows it is shown."""

    def __init__(self, sql_for: dict[str, str]):
        self.sql_for = sql_for

    def answer(self, prompt: str) -> str:
        question = prompt.split("Question: ", 1)[1].split("\n", 1)[0]
        if prompt.rstrip().endswith("SQLQuery:"):
            assert "READ-ONLY" in prompt and "SELECT *" in prompt, "prompt must carry the secure SQL rules"
            return self.sql_for[question]
        return "Rows: " + prompt.split("SQL result rows: ", 1)[1].split("\n", 1)[0]


def fake_sql_models(sql_for: dict[str, str]) -> Models:
    return Models(answer=FakeSqlModel(sql_for), embed=FakeEmbeddings())
