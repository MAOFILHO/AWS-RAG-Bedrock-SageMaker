"""Offline checks of the Bedrock wrappers: botocore's Stubber validates each request
against the real bedrock-runtime API shape, with no network and no AWS account."""

import io
import json

import boto3
import pytest
from botocore.exceptions import ClientError
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


def client_error(code):
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, "Converse")


class FlakyClient:
    """Raises each scripted error in turn, then returns a Converse answer."""

    def __init__(self, *errors):
        self.errors, self.calls = list(errors), 0

    def converse(self, **_):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return {"output": {"message": {"content": [{"text": "ok"}]}}}


def answer_with(client, waits):
    return BedrockAnswerModel(client, "m", sleep=waits.append).answer("p")


def test_a_transient_error_is_retried_and_the_answer_returned():
    client, waits = FlakyClient(client_error("ModelErrorException")), []
    assert answer_with(client, waits) == "ok"
    assert (client.calls, len(waits)) == (2, 1)


def test_the_wait_grows_with_each_failed_try():
    errors = [client_error("ThrottlingException"), client_error("ThrottlingException")]
    client, waits = FlakyClient(*errors), []
    assert answer_with(client, waits) == "ok"
    assert waits == [1.0, 2.0]


def test_an_error_with_no_response_raises_the_original_error():
    error = Exception("boom")
    error.response = None
    client, waits = FlakyClient(error), []
    with pytest.raises(Exception) as raised:
        answer_with(client, waits)
    assert raised.value is error
    assert (client.calls, waits) == (1, [])


def test_three_transient_failures_raise_the_original_error_with_no_fourth_try():
    errors = [client_error("ModelErrorException") for _ in range(4)]
    client, waits = FlakyClient(*errors), []
    with pytest.raises(ClientError) as raised:
        answer_with(client, waits)
    assert raised.value is errors[2]
    assert (client.calls, len(waits)) == (3, 2)


def test_a_non_transient_error_is_not_retried():
    client, waits = FlakyClient(client_error("AccessDeniedException")), []
    with pytest.raises(ClientError):
        answer_with(client, waits)
    assert (client.calls, waits) == (1, [])


def test_the_embedding_call_is_retried_too():
    class FlakyEmbedClient:
        calls = 0

        def invoke_model(self, **_):
            self.calls += 1
            if self.calls == 1:
                raise client_error("ThrottlingException")
            return {"body": io.BytesIO(json.dumps({"embedding": [1.0]}).encode())}

    client = FlakyEmbedClient()
    assert BedrockEmbeddingModel(client, "e", sleep=lambda _: None).embed(["t"]) == [[1.0]]
    assert client.calls == 2
