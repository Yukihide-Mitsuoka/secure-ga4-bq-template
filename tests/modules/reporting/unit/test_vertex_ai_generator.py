from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.modules.reporting.application.ports import ProviderError
from src.modules.reporting.infrastructure.vertex_ai_generator import VertexAiGenerator


class FakeModels:
    def __init__(self, text: str = '{"executive_summary":"ok","findings":[]}') -> None:
        self.text = text
        self.call = None

    def generate_content(self, **kwargs):
        self.call = kwargs
        return SimpleNamespace(text=self.text)


class FakeClient:
    def __init__(self) -> None:
        self.models = FakeModels()
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_vertex_adapter_uses_v1_structured_output_and_closes_client() -> None:
    client = FakeClient()
    factory_args = {}

    def factory(**kwargs):
        factory_args.update(kwargs)
        return client

    result = VertexAiGenerator(
        project="project", location="global", model="gemini", client_factory=factory
    ).generate('{"findings":[]}')

    assert result.provider == "vertex-ai"
    assert factory_args["vertexai"] is True
    assert factory_args["http_options"].api_version == "v1"
    assert client.models.call["config"].response_mime_type == "application/json"
    assert client.models.call["config"].tools is None
    assert client.closed


def test_vertex_adapter_translates_provider_failure_and_closes_client() -> None:
    client = FakeClient()

    def fail(**kwargs):
        raise RuntimeError("provider body")

    client.models.generate_content = fail
    generator = VertexAiGenerator(
        project="project", location="global", model="gemini", client_factory=lambda **_: client
    )

    with pytest.raises(ProviderError, match="Vertex AI report generation failed"):
        generator.generate("{}")
    assert client.closed


def test_vertex_adapter_translates_response_text_failure() -> None:
    client = FakeClient()

    class BrokenResponse:
        @property
        def text(self):
            raise RuntimeError("unsafe response body")

    client.models.generate_content = lambda **_: BrokenResponse()
    generator = VertexAiGenerator(
        project="project", location="global", model="gemini", client_factory=lambda **_: client
    )

    with pytest.raises(ProviderError, match="Vertex AI report generation failed"):
        generator.generate("{}")
