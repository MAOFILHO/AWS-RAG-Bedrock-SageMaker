"""Core: settings, Bedrock models, the numpy store and the prompt step every Pipeline uses."""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, ContextManager, Mapping, Protocol

import numpy as np

DONT_KNOW = "I don't know based on the provided documents."

WEB_PROMPT = f"""You are a helpful assistant.
Answer the question using ONLY the context provided below.
If the answer is not in the context, say: "{DONT_KNOW}"
Keep your answer concise and accurate.

Context:
{{context}}

Question: {{question}}

Answer:"""

NOT_ENOUGH_INFO = "I do not have sufficient information in the provided document."

PDF_PROMPT = f"""You are a helpful assistant.
Answer the question STRICTLY using the context provided below. Do NOT use any external knowledge.
If the answer is not in the context, respond with: "{NOT_ENOUGH_INFO}"

Context:
{{context}}

Question: {{question}}

Answer:"""


@dataclass(frozen=True)
class Settings:
    model_id: str = "amazon.nova-lite-v1:0"
    embed_model_id: str = "amazon.titan-embed-text-v2:0"
    region: str = "us-east-1"
    langsmith_api_key: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        default = cls()
        return cls(
            model_id=env.get("RAG_MODEL_ID") or default.model_id,
            embed_model_id=env.get("RAG_EMBED_MODEL_ID") or default.embed_model_id,
            region=env.get("AWS_REGION") or default.region,
            langsmith_api_key=env.get("LANGSMITH_API_KEY") or None,
        )


TRACING_PROJECT = "K21"


def tracing(settings: Settings, make_client: Callable | None = None) -> ContextManager:
    """Trace runs in LangSmith while a key is set; with no key, force tracing off and build no client."""
    from langsmith import Client, tracing_context

    if not settings.langsmith_api_key:
        return tracing_context(enabled=False)

    client = (make_client or Client)(api_key=settings.langsmith_api_key)
    return tracing_context(enabled=True, client=client, project_name=TRACING_PROJECT)


class AnswerModel(Protocol):
    def answer(self, prompt: str) -> str: ...


class EmbeddingModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class Models:
    answer: AnswerModel
    embed: EmbeddingModel


TRANSIENT_ERRORS = {
    "ModelErrorException",
    "ModelTimeoutException",
    "ThrottlingException",
    "ServiceUnavailableException",
    "InternalServerException",
}
TRIES, WAIT_SECONDS = 3, 1.0


def with_retry(call: Callable, sleep: Callable[[float], None]):
    """Run call, retrying a transient Bedrock error up to TRIES times in all; raise the last error."""
    for attempt in range(1, TRIES + 1):
        try:
            return call()
        except Exception as error:
            code = (getattr(error, "response", None) or {}).get("Error", {}).get("Code")
            if code not in TRANSIENT_ERRORS or attempt == TRIES:
                raise
            sleep(WAIT_SECONDS * attempt)


class BedrockAnswerModel:
    def __init__(self, client, model_id: str, sleep: Callable[[float], None] = time.sleep):
        self.client, self.model_id, self.sleep = client, model_id, sleep
        self.input_tokens = self.output_tokens = 0

    def answer(self, prompt: str) -> str:
        response = with_retry(
            lambda: self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"temperature": 0},
            ),
            self.sleep,
        )
        usage = response.get("usage", {})
        self.input_tokens += usage.get("inputTokens", 0)
        self.output_tokens += usage.get("outputTokens", 0)
        return response["output"]["message"]["content"][0]["text"]


class BedrockEmbeddingModel:
    def __init__(self, client, model_id: str, sleep: Callable[[float], None] = time.sleep):
        self.client, self.model_id, self.sleep = client, model_id, sleep

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            response = with_retry(
                lambda: self.client.invoke_model(
                    modelId=self.model_id, body=json.dumps({"inputText": text})
                ),
                self.sleep,
            )
            vectors.append(json.loads(response["body"].read())["embedding"])
        return vectors


def bedrock_models(settings: Settings) -> Models:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.region)
    return Models(
        answer=BedrockAnswerModel(client, settings.model_id),
        embed=BedrockEmbeddingModel(client, settings.embed_model_id),
    )


@dataclass(frozen=True)
class Chunk:
    text: str
    source: str


class VectorStore:
    """Cosine-similarity store over numpy, as in the notebooks."""

    def __init__(self, embed: EmbeddingModel, chunks: list[Chunk]):
        self.embed, self.chunks = embed, chunks
        self.vectors = np.array(embed.embed([c.text for c in chunks]))

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        query_vec = np.array(self.embed.embed([query])[0])
        norms = np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query_vec)
        scores = self.vectors @ query_vec / np.where(norms == 0, 1e-10, norms)
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]


def format_docs(chunks: list[Chunk]) -> str:
    return "\n\n".join(c.text for c in chunks)


def answer_with_context(
    question: str, store: VectorStore, models: Models, prompt: str, k: int = 3
) -> tuple[str, str]:
    """Return the answer and the context it was given."""
    context = format_docs([chunk for chunk, _ in store.search(question, k)])
    return models.answer.answer(prompt.format(context=context, question=question)).strip(), context


def answer_from(
    question: str, chunks: list[Chunk], models: Models, prompt: str, k: int = 3
) -> str:
    return answer_with_context(question, VectorStore(models.embed, chunks), models, prompt, k)[0]
