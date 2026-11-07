"""Offline checks of the Bedrock wrappers: botocore's Stubber validates each request
against the real bedrock-runtime API shape, with no network and no AWS account."""

import io
import json

import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber

from rag_course.core import BedrockAnswerModel, BedrockEmbeddingModel, Settings, bedrock_models


def stubbed_client():
    client = boto3.client(
        "bedrock-runtime",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    return client, Stubber(client)


def test_answer_model_sends_a_converse_request_and_reads_the_text():
    client, stub = stubbed_client()
    stub.add_response(
        "converse",
        {
            "output": {"message": {"role": "assistant", "content": [{"text": "Cloud computing is on-demand IT."}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 6, "totalTokens": 16},
            "metrics": {"latencyMs": 5},
        },
        {
            "modelId": "amazon.nova-lite-v1:0",
            "messages": [{"role": "user", "content": [{"text": "the prompt"}]}],
            "inferenceConfig": {"temperature": 0},
        },
    )
    with stub:
        answer = BedrockAnswerModel(client, "amazon.nova-lite-v1:0").answer("the prompt")
    stub.assert_no_pending_responses()
    assert answer == "Cloud computing is on-demand IT."


def test_embedding_model_sends_one_titan_request_per_text():
    client, stub = stubbed_client()
    for text, vector in (("first", [0.1, 0.2]), ("second", [0.3, 0.4])):
        payload = json.dumps({"embedding": vector, "inputTextTokenCount": 1}).encode()
        stub.add_response(
            "invoke_model",
            {"body": StreamingBody(io.BytesIO(payload), len(payload)), "contentType": "application/json"},
            {"modelId": "amazon.titan-embed-text-v2:0", "body": json.dumps({"inputText": text})},
        )
    with stub:
        vectors = BedrockEmbeddingModel(client, "amazon.titan-embed-text-v2:0").embed(["first", "second"])
    stub.assert_no_pending_responses()
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_bedrock_models_use_the_settings_region_and_model_ids():
    models = bedrock_models(Settings("m", "e", "eu-west-1"))
    assert models.answer.client.meta.region_name == "eu-west-1"
    assert (models.answer.model_id, models.embed.model_id) == ("m", "e")
