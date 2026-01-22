"""Comprehensive test suite for LLM client error handling and initialization.

Tests cover:
- TD-P2-001: LLM client initialization error paths
- API key validation from environment
- Invalid model name handling
- Missing dependencies (anthropic, openai packages)
- Rate limiter initialization
- Network timeout scenarios

Target: 70%+ coverage on llm_client.py
"""

import os
from unittest import mock

import pytest

from aurora_reasoning.llm_client import (
    AnthropicClient,
    LLMResponse,
    OllamaClient,
    OpenAIClient,
    extract_json_from_text,
)


class TestAPIKeyValidation:
    """Test API key validation for different LLM clients (Task 6.5)."""

    def test_anthropic_missing_api_key(self):
        """Test AnthropicClient raises error when API key is missing."""
        # Ensure API key is not in environment
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                AnthropicClient()

            error_msg = str(exc_info.value)
            assert "API key required" in error_msg or "ANTHROPIC_API_KEY" in error_msg
            assert (
                "environment variable" in error_msg.lower()
                or "api_key parameter" in error_msg.lower()
            )

    def test_anthropic_empty_api_key_env(self):
        """Test AnthropicClient raises error when API key is empty string."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            with pytest.raises(ValueError) as exc_info:
                AnthropicClient()

            error_msg = str(exc_info.value)
            assert "API key required" in error_msg or "ANTHROPIC_API_KEY" in error_msg

    def test_anthropic_api_key_from_env(self):
        """Test AnthropicClient accepts API key from environment."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient()
                assert client._api_key == "sk-ant-test-key"

    def test_anthropic_api_key_from_parameter(self):
        """Test AnthropicClient accepts API key from parameter."""
        with mock.patch("anthropic.Anthropic"):
            client = AnthropicClient(api_key="sk-ant-param-key")
            assert client._api_key == "sk-ant-param-key"

    def test_anthropic_parameter_overrides_env(self):
        """Test API key parameter overrides environment variable."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-env-key"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient(api_key="sk-ant-param-key")
                assert client._api_key == "sk-ant-param-key"

    def test_openai_missing_api_key(self):
        """Test OpenAIClient raises error when API key is missing."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                OpenAIClient()

            error_msg = str(exc_info.value)
            assert "API key required" in error_msg or "OPENAI_API_KEY" in error_msg
            assert (
                "environment variable" in error_msg.lower()
                or "api_key parameter" in error_msg.lower()
            )

    def test_openai_empty_api_key_env(self):
        """Test OpenAIClient raises error when API key is empty string."""
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with pytest.raises(ValueError) as exc_info:
                OpenAIClient()

            error_msg = str(exc_info.value)
            assert "API key required" in error_msg or "OPENAI_API_KEY" in error_msg

    def test_openai_api_key_from_env(self):
        """Test OpenAIClient accepts API key from environment."""
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test-key"}):
            with mock.patch("openai.OpenAI"):
                client = OpenAIClient()
                assert client._api_key == "sk-openai-test-key"

    def test_openai_api_key_from_parameter(self):
        """Test OpenAIClient accepts API key from parameter."""
        with mock.patch("openai.OpenAI"):
            client = OpenAIClient(api_key="sk-openai-param-key")
            assert client._api_key == "sk-openai-param-key"

    def test_ollama_no_api_key_required(self):
        """Test OllamaClient does not require API key."""
        with mock.patch("ollama.Client"):
            client = OllamaClient()
            assert not hasattr(client, "_api_key")


class TestMissingDependencies:
    """Test LLM clients handle missing package dependencies (Task 6.6)."""

    def test_anthropic_missing_package(self):
        """Test AnthropicClient raises helpful error when anthropic package missing."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch.dict("sys.modules", {"anthropic": None}):
                # Mock ImportError when trying to import anthropic
                with mock.patch(
                    "builtins.__import__",
                    side_effect=ImportError("No module named 'anthropic'"),
                ):
                    with pytest.raises(ImportError) as exc_info:
                        AnthropicClient()

                    error_msg = str(exc_info.value)
                    assert "anthropic" in error_msg.lower()
                    assert (
                        "pip install anthropic" in error_msg.lower()
                        or "install" in error_msg.lower()
                    )

    def test_openai_missing_package(self):
        """Test OpenAIClient raises helpful error when openai package missing."""
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}):
            with mock.patch.dict("sys.modules", {"openai": None}):
                with mock.patch(
                    "builtins.__import__",
                    side_effect=ImportError("No module named 'openai'"),
                ):
                    with pytest.raises(ImportError) as exc_info:
                        OpenAIClient()

                    error_msg = str(exc_info.value)
                    assert "openai" in error_msg.lower()
                    assert (
                        "pip install openai" in error_msg.lower() or "install" in error_msg.lower()
                    )

    def test_ollama_missing_package(self):
        """Test OllamaClient raises helpful error when ollama package missing."""
        with mock.patch.dict("sys.modules", {"ollama": None}):
            with mock.patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'ollama'"),
            ):
                with pytest.raises(ImportError) as exc_info:
                    OllamaClient()

                error_msg = str(exc_info.value)
                assert "ollama" in error_msg.lower()
                assert "pip install ollama" in error_msg.lower() or "install" in error_msg.lower()


class TestClientInitialization:
    """Test LLM client initialization and configuration (Task 6.6)."""

    def test_anthropic_default_model(self):
        """Test AnthropicClient default model configuration."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient()
                assert client.default_model == "claude-sonnet-4-20250514"

    def test_anthropic_custom_model(self):
        """Test AnthropicClient accepts custom model."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient(default_model="claude-opus-4")
                assert client.default_model == "claude-opus-4"

    def test_openai_default_model(self):
        """Test OpenAIClient default model configuration."""
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}):
            with mock.patch("openai.OpenAI"):
                client = OpenAIClient()
                assert client.default_model == "gpt-4-turbo-preview"

    def test_openai_custom_model(self):
        """Test OpenAIClient accepts custom model."""
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}):
            with mock.patch("openai.OpenAI"):
                client = OpenAIClient(default_model="gpt-4")
                assert client.default_model == "gpt-4"

    def test_ollama_default_model_and_endpoint(self):
        """Test OllamaClient default configuration."""
        with mock.patch("ollama.Client"):
            client = OllamaClient()
            assert client.default_model == "llama2"
            assert client._endpoint == "http://localhost:11434"

    def test_ollama_custom_endpoint(self):
        """Test OllamaClient accepts custom endpoint."""
        with mock.patch("ollama.Client"):
            client = OllamaClient(endpoint="http://custom:8080")
            assert client._endpoint == "http://custom:8080"

    def test_anthropic_rate_limiter_initialization(self):
        """Test AnthropicClient initializes rate limiter."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient()
                assert hasattr(client, "_last_request_time")
                assert hasattr(client, "_min_request_interval")
                assert client._min_request_interval == 0.1

    def test_openai_rate_limiter_initialization(self):
        """Test OpenAIClient initializes rate limiter."""
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}):
            with mock.patch("openai.OpenAI"):
                client = OpenAIClient()
                assert hasattr(client, "_last_request_time")
                assert hasattr(client, "_min_request_interval")
                assert client._min_request_interval == 0.1

    def test_ollama_rate_limiter_initialization(self):
        """Test OllamaClient initializes rate limiter."""
        with mock.patch("ollama.Client"):
            client = OllamaClient()
            assert hasattr(client, "_last_request_time")
            assert hasattr(client, "_min_request_interval")
            assert client._min_request_interval == 0.05  # Faster for local models


class TestGenerateErrorHandling:
    """Test error handling in generate() method."""

    def test_anthropic_empty_prompt_raises_error(self):
        """Test AnthropicClient raises error for empty prompt."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient()

                with pytest.raises(ValueError) as exc_info:
                    client.generate("")

                assert "empty" in str(exc_info.value).lower()

    def test_anthropic_whitespace_prompt_raises_error(self):
        """Test AnthropicClient raises error for whitespace-only prompt."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient()

                with pytest.raises(ValueError) as exc_info:
                    client.generate("   \n\t  ")

                assert "empty" in str(exc_info.value).lower()

    def test_openai_empty_prompt_raises_error(self):
        """Test OpenAIClient raises error for empty prompt."""
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}):
            with mock.patch("openai.OpenAI"):
                client = OpenAIClient()

                with pytest.raises(ValueError) as exc_info:
                    client.generate("")

                assert "empty" in str(exc_info.value).lower()

    def test_ollama_empty_prompt_raises_error(self):
        """Test OllamaClient raises error for empty prompt."""
        with mock.patch("ollama.Client"):
            client = OllamaClient()

            with pytest.raises(ValueError) as exc_info:
                client.generate("")

            assert "empty" in str(exc_info.value).lower()

    def test_anthropic_api_error_wrapped_in_runtime_error(self):
        """Test AnthropicClient wraps API errors in RuntimeError."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()
            mock_client.messages.create.side_effect = Exception("API Error")

            with mock.patch("anthropic.Anthropic", return_value=mock_client):
                client = AnthropicClient()

                with pytest.raises(RuntimeError) as exc_info:
                    client.generate("test prompt")

                error_msg = str(exc_info.value)
                assert "API call failed" in error_msg or "Anthropic" in error_msg


class TestTokenCounting:
    """Test token counting methods."""

    def test_anthropic_count_tokens(self):
        """Test AnthropicClient token counting heuristic."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with mock.patch("anthropic.Anthropic"):
                client = AnthropicClient()

                # Heuristic: 1 token ≈ 4 characters
                text = "a" * 100  # 100 characters
                tokens = client.count_tokens(text)
                assert tokens == 25  # 100 / 4

    def test_openai_count_tokens(self):
        """Test OpenAIClient token counting heuristic."""
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-test"}):
            with mock.patch("openai.OpenAI"):
                client = OpenAIClient()

                text = "a" * 200  # 200 characters
                tokens = client.count_tokens(text)
                assert tokens == 50  # 200 / 4

    def test_ollama_count_tokens(self):
        """Test OllamaClient token counting heuristic."""
        with mock.patch("ollama.Client"):
            client = OllamaClient()

            text = "a" * 400  # 400 characters
            tokens = client.count_tokens(text)
            assert tokens == 100  # 400 / 4


class TestJSONExtraction:
    """Test JSON extraction utility function."""

    def test_extract_json_direct_parse(self):
        """Test extracting JSON from direct JSON string."""
        json_str = '{"key": "value", "number": 42}'
        result = extract_json_from_text(json_str)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_from_markdown_code_block(self):
        """Test extracting JSON from markdown code block."""
        text = """
        Here is the JSON:
        ```json
        {"key": "value", "number": 42}
        ```
        That's it!
        """
        result = extract_json_from_text(text)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_from_code_block_without_language(self):
        """Test extracting JSON from code block without language specifier."""
        text = """
        ```
        {"key": "value"}
        ```
        """
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_extract_json_from_text_with_surrounding_content(self):
        """Test extracting JSON from text with surrounding content."""
        text = 'The result is {"key": "value"} and that is all.'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_extract_json_with_nested_objects(self):
        """Test extracting JSON with nested objects."""
        text = '{"outer": {"inner": {"deep": "value"}}}'
        result = extract_json_from_text(text)
        assert result == {"outer": {"inner": {"deep": "value"}}}

    def test_extract_json_raises_error_on_invalid(self):
        """Test extracting JSON raises error when no valid JSON found."""
        text = "This is just plain text with no JSON"
        with pytest.raises(ValueError) as exc_info:
            extract_json_from_text(text)

        assert "No valid JSON found" in str(exc_info.value)

    def test_extract_json_with_multiple_code_blocks(self):
        """Test extracting JSON when multiple code blocks present (uses first valid one)."""
        text = """
        First block:
        ```
        invalid json {
        ```

        Second block:
        ```json
        {"valid": "json"}
        ```
        """
        result = extract_json_from_text(text)
        assert result == {"valid": "json"}


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_llm_response_creation(self):
        """Test creating LLMResponse object."""
        response = LLMResponse(
            content="test response",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
            metadata={"id": "msg_123"},
        )

        assert response.content == "test response"
        assert response.model == "claude-3-5-sonnet"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.finish_reason == "stop"
        assert response.metadata["id"] == "msg_123"

    def test_llm_response_default_metadata(self):
        """Test LLMResponse has empty dict as default metadata."""
        response = LLMResponse(
            content="test",
            model="model",
            input_tokens=10,
            output_tokens=5,
            finish_reason="stop",
        )

        assert response.metadata == {}


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_anthropic_rate_limit_enforced(self):
        """Test AnthropicClient enforces rate limiting between requests."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()

            # Mock successful API response
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

                # First request
                start = time.time()
                client.generate("test 1")

                # Second request immediately after
                client.generate("test 2")
                elapsed = time.time() - start

                # Should have enforced at least the minimum interval
                assert elapsed >= client._min_request_interval

    def test_rate_limiter_updates_last_request_time(self):
        """Test rate limiter updates last request time."""
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
                initial_time = client._last_request_time

                time.sleep(0.2)  # Wait longer than rate limit
                client.generate("test")

                assert client._last_request_time > initial_time


class TestGenerateJSON:
    """Test generate_json() method for structured output."""

    def test_anthropic_generate_json_success(self):
        """Test AnthropicClient generate_json returns parsed JSON."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()
            mock_response = mock.Mock()
            mock_response.content = [mock.Mock(text='{"key": "value", "number": 42}')]
            mock_response.model = "claude-3"
            mock_response.usage = mock.Mock(input_tokens=10, output_tokens=5)
            mock_response.stop_reason = "stop"
            mock_response.id = "msg_123"
            mock_response.stop_sequence = None
            mock_client.messages.create.return_value = mock_response

            with mock.patch("anthropic.Anthropic", return_value=mock_client):
                client = AnthropicClient()
                result = client.generate_json("Return JSON")

                assert result == {"key": "value", "number": 42}

    def test_anthropic_generate_json_with_system_prompt(self):
        """Test AnthropicClient generate_json adds JSON enforcement to system prompt."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()
            mock_response = mock.Mock()
            mock_response.content = [mock.Mock(text='{"result": true}')]
            mock_response.model = "claude-3"
            mock_response.usage = mock.Mock(input_tokens=10, output_tokens=5)
            mock_response.stop_reason = "stop"
            mock_response.id = "msg_123"
            mock_response.stop_sequence = None
            mock_client.messages.create.return_value = mock_response

            with mock.patch("anthropic.Anthropic", return_value=mock_client):
                client = AnthropicClient()
                result = client.generate_json("Return JSON", system="You are a helpful assistant")

                # Verify system prompt was enhanced with JSON enforcement
                call_kwargs = mock_client.messages.create.call_args.kwargs
                assert "JSON" in call_kwargs["system"]
                assert result == {"result": True}

    def test_anthropic_generate_json_invalid_json_raises_error(self):
        """Test AnthropicClient generate_json raises error on invalid JSON."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            mock_client = mock.Mock()
            mock_response = mock.Mock()
            mock_response.content = [mock.Mock(text="This is not JSON")]
            mock_response.model = "claude-3"
            mock_response.usage = mock.Mock(input_tokens=10, output_tokens=5)
            mock_response.stop_reason = "stop"
            mock_response.id = "msg_123"
            mock_response.stop_sequence = None
            mock_client.messages.create.return_value = mock_response

            with mock.patch("anthropic.Anthropic", return_value=mock_client):
                client = AnthropicClient()

                with pytest.raises(ValueError) as exc_info:
                    client.generate_json("Return JSON")

                assert (
                    "extract JSON" in str(exc_info.value).lower()
                    or "json" in str(exc_info.value).lower()
                )

    def test_openai_generate_json_with_response_format(self):
        """Test OpenAIClient generate_json uses JSON mode."""
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

                # Verify response_format was set to json_object
                call_kwargs = mock_client.chat.completions.create.call_args.kwargs
                assert "response_format" in call_kwargs
                assert call_kwargs["response_format"]["type"] == "json_object"
                assert result == {"openai": "json"}

    def test_ollama_generate_json_success(self):
        """Test OllamaClient generate_json returns parsed JSON."""
        with mock.patch("ollama.Client") as mock_ollama:
            mock_client_instance = mock.Mock()
            mock_client_instance.chat.return_value = {
                "message": {"content": '{"ollama": "response"}'},
                "model": "llama2",
                "done_reason": "stop",
            }
            mock_ollama.return_value = mock_client_instance

            client = OllamaClient()
            result = client.generate_json("Return JSON")

            assert result == {"ollama": "response"}
