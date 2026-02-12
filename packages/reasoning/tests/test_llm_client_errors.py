"""Tests for LLM client error handling, initialization, and JSON extraction."""

import os
from unittest import mock

import pytest

from aurora_reasoning.llm_client import (
    AnthropicClient,
    OllamaClient,
    OpenAIClient,
    extract_json_from_text,
)


class TestAPIKeyValidation:
    """Test API key validation for LLM clients."""

    def test_anthropic_missing_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key|ANTHROPIC_API_KEY"):
                AnthropicClient()

    def test_anthropic_empty_api_key(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            with pytest.raises(ValueError, match="API key|ANTHROPIC_API_KEY"):
                AnthropicClient()

    def test_anthropic_key_from_param_overrides_env(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-env"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient(api_key="sk-ant-param")
                assert client._api_key == "sk-ant-param"

    def test_openai_missing_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key|OPENAI_API_KEY"):
                OpenAIClient()

    def test_ollama_no_api_key_required(self):
        with mock.patch("ollama.Client"):
            client = OllamaClient()
            assert not hasattr(client, "_api_key")


class TestMissingDependencies:
    """Test LLM clients handle missing package dependencies."""

    def test_anthropic_missing_package(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch.dict("sys.modules", {"anthropic": None}):
                with mock.patch(
                    "builtins.__import__",
                    side_effect=ImportError("No module named 'anthropic'"),
                ):
                    with pytest.raises(ImportError, match="anthropic"):
                        AnthropicClient()

    def test_openai_missing_package(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}):
            with mock.patch.dict("sys.modules", {"openai": None}):
                with mock.patch(
                    "builtins.__import__",
                    side_effect=ImportError("No module named 'openai'"),
                ):
                    with pytest.raises(ImportError, match="openai"):
                        OpenAIClient()


class TestClientInitialization:
    """Test LLM client initialization."""

    def test_anthropic_default_model(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient()
                assert client.default_model == "claude-sonnet-4-20250514"

    def test_anthropic_custom_model(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient(default_model="claude-opus-4")
                assert client.default_model == "claude-opus-4"

    def test_ollama_default_config(self):
        with mock.patch("ollama.Client"):
            client = OllamaClient()
            assert client.default_model == "llama2"
            assert client._endpoint == "http://localhost:11434"


class TestGenerateErrorHandling:
    """Test error handling in generate() method."""

    def test_anthropic_empty_prompt(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient()
                with pytest.raises(ValueError, match="(?i)empty"):
                    client.generate("")

    def test_anthropic_api_error_wrapped(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()
            mock_client.messages.create.side_effect = Exception("API Error")
            with mock.patch("anthropic.Anthropic", return_value=mock_client):
                client = AnthropicClient()
                with pytest.raises(RuntimeError, match="API call failed|Anthropic"):
                    client.generate("test prompt")


class TestJSONExtraction:
    """Test JSON extraction utility function."""

    def test_direct_json(self):
        result = extract_json_from_text('{"key": "value", "number": 42}')
        assert result == {"key": "value", "number": 42}

    def test_from_markdown_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert extract_json_from_text(text) == {"key": "value"}

    def test_from_surrounding_text(self):
        text = 'The result is {"key": "value"} and that is all.'
        assert extract_json_from_text(text) == {"key": "value"}

    def test_nested_objects(self):
        text = '{"outer": {"inner": {"deep": "value"}}}'
        assert extract_json_from_text(text) == {"outer": {"inner": {"deep": "value"}}}

    def test_invalid_raises_error(self):
        with pytest.raises(ValueError, match="No valid JSON"):
            extract_json_from_text("This is just plain text")


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_anthropic_rate_limit_enforced(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()
            mock_response = mock.Mock()
            mock_response.content = [mock.Mock(text="response")]
            mock_response.model = "claude-3"
            mock_response.usage = mock.Mock(input_tokens=10, output_tokens=5)
            mock_response.stop_reason = "stop"
            mock_response.id = "msg_123"
            mock_response.stop_sequence = None
            mock_client.messages.create.return_value = mock_response

            with mock.patch("anthropic.Anthropic", return_value=mock_client):
                import time

                client = AnthropicClient()
                start = time.time()
                client.generate("test 1")
                client.generate("test 2")
                elapsed = time.time() - start
                assert elapsed >= client._min_request_interval


class TestGenerateJSON:
    """Test generate_json() method for structured output."""

    def test_anthropic_generate_json_success(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()
            mock_response = mock.Mock()
            mock_response.content = [mock.Mock(text='{"key": "value"}')]
            mock_response.model = "claude-3"
            mock_response.usage = mock.Mock(input_tokens=10, output_tokens=5)
            mock_response.stop_reason = "stop"
            mock_response.id = "msg_123"
            mock_response.stop_sequence = None
            mock_client.messages.create.return_value = mock_response

            with mock.patch("anthropic.Anthropic", return_value=mock_client):
                client = AnthropicClient()
                assert client.generate_json("Return JSON") == {"key": "value"}

    def test_anthropic_generate_json_invalid_raises(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()
            mock_response = mock.Mock()
            mock_response.content = [mock.Mock(text="Not JSON")]
            mock_response.model = "claude-3"
            mock_response.usage = mock.Mock(input_tokens=10, output_tokens=5)
            mock_response.stop_reason = "stop"
            mock_response.id = "msg_123"
            mock_response.stop_sequence = None
            mock_client.messages.create.return_value = mock_response

            with mock.patch("anthropic.Anthropic", return_value=mock_client):
                client = AnthropicClient()
                with pytest.raises(ValueError, match="(?i)json"):
                    client.generate_json("Return JSON")

    def test_openai_generate_json_uses_json_mode(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}):
            mock_client = mock.Mock()
            mock_choice = mock.Mock()
            mock_choice.message.content = '{"openai": "json"}'
            mock_choice.finish_reason = "stop"
            mock_response = mock.Mock()
            mock_response.choices = [mock_choice]
            mock_response.model = "gpt-4"
            mock_response.usage = mock.Mock(prompt_tokens=10, completion_tokens=5)
            mock_response.id = "chat_123"
            mock_response.created = 1234567890
            mock_client.chat.completions.create.return_value = mock_response

            with mock.patch("openai.OpenAI", return_value=mock_client):
                client = OpenAIClient()
                result = client.generate_json("Return JSON")
                call_kwargs = mock_client.chat.completions.create.call_args.kwargs
                assert call_kwargs["response_format"]["type"] == "json_object"
                assert result == {"openai": "json"}
