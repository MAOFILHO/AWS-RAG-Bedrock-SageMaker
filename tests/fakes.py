"""Fake Bedrock answer and embedding models, and the saved web pages, for Offline tests."""

import gzip
import re
import zlib
from pathlib import Path

from rag_course.core import DONT_KNOW, NOT_ENOUGH_INFO, Models

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
        fixed = next((s for s in (DONT_KNOW, NOT_ENOUGH_INFO) if s in prompt), None)
        assert fixed, "prompt must carry a fixed I-don't-know sentence"
        context = prompt.split("Context:\n", 1)[1].split("\n\nQuestion: ", 1)[0]
        question = prompt.split("\n\nQuestion: ", 1)[1].split("\n\nAnswer:", 1)[0]
        wanted = words(question)
        lines = [line for line in context.splitlines() if wanted and wanted <= words(line)]
        return max(lines, key=len) if lines else fixed


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


def text_pdf(lines: list[str]) -> bytes:
    """A one-page PDF holding the given lines of text, built by hand."""
    text = " ".join(f"({line}) Tj 0 -14 Td" for line in lines)
    stream = f"BT /F1 12 Tf 72 720 Td {text} ET".encode()
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        b"<</Length %d>>stream\n%s\nendstream" % (len(stream), stream),
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)
