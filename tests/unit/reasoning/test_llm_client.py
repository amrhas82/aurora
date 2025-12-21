"""Unit tests for LLM client interface and implementations."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from aurora_reasoning.llm_client import (
    AnthropicClient,
    LLMClient,
    LLMResponse,
    OpenAIClient,
    OllamaClient,
    extract_json_from_text,
)


class TestLLMResponse:
    """Test LLMResponse model."""

    def test_create_response(self):
        """Test creating LLMResponse."""
        response = LLMResponse(
            content="Hello, world!",
            model="test-model",
            input_tokens=10,
            output_tokens=3,
            finish_reason="stop",
        )
        assert response.content == "Hello, world!"
        assert response.model == "test-model"
        assert response.input_tokens == 10
        assert response.output_tokens == 3
        assert response.finish_reason == "stop"
        assert response.metadata == {}


class TestExtractJSON:
    """Test JSON extraction from text."""

    def test_direct_json(self):
        """Test extracting direct JSON."""
        text = '{"key": "value"}'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_json_with_markdown(self):
        """Test extracting JSON from markdown code block."""
        text = '''Here is the result:
```json
{"key": "value"}
```
Hope this helps!'''
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_json_in_code_block_no_language(self):
        """Test extracting JSON from code block without language specifier."""
        text = '''```
{"key": "value"}
```'''
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_json_in_text(self):
        """Test extracting JSON embedded in text."""
        text = 'Some text before {"key": "value"} and after'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_invalid_json(self):
        """Test error on invalid JSON."""
        text = "This is not JSON at all"
        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json_from_text(text)


class TestAnthropicClient:
    """Test AnthropicClient implementation."""

    def test_initialization_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch("aurora_reasoning.llm_client.anthropic"):
            client = AnthropicClient(api_key="test-key")
            assert client._api_key == "test-key"
            assert client.default_model == "claude-sonnet-4-20250514"

    def test_initialization_from_env(self):
        """Test initialization from environment variable."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            with patch("aurora_reasoning.llm_client.anthropic"):
                client = AnthropicClient()
                assert client._api_key == "env-key"

    def test_initialization_no_api_key(self):
        """Test error when no API key provided."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key required"):
                AnthropicClient()

    @patch("aurora_reasoning.llm_client.anthropic")
    def test_generate(self, mock_anthropic):
        """Test generate method."""
        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated response")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        client = AnthropicClient(api_key="test-key")
        response = client.generate("Test prompt")

        assert response.content == "Generated response"
        assert response.model == "claude-sonnet-4-20250514"
        assert response.input_tokens == 10
        assert response.output_tokens == 5
        assert response.finish_reason == "end_turn"

    @patch("aurora_reasoning.llm_client.anthropic")
    def test_generate_empty_prompt(self, mock_anthropic):
        """Test error on empty prompt."""
        mock_anthropic.Anthropic.return_value = MagicMock()
        client = AnthropicClient(api_key="test-key")

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate("")

    @patch("aurora_reasoning.llm_client.anthropic")
    def test_generate_json(self, mock_anthropic):
        """Test generate_json method."""
        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"result": "success"}')]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        client = AnthropicClient(api_key="test-key")
        result = client.generate_json("Test prompt")

        assert result == {"result": "success"}

    def test_count_tokens(self):
        """Test token counting."""
        with patch("aurora_reasoning.llm_client.anthropic"):
            client = AnthropicClient(api_key="test-key")
            tokens = client.count_tokens("This is a test")
            assert tokens == len("This is a test") // 4


class TestOpenAIClient:
    """Test OpenAIClient implementation."""

    def test_initialization_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch("aurora_reasoning.llm_client.openai"):
            client = OpenAIClient(api_key="test-key")
            assert client._api_key == "test-key"
            assert client.default_model == "gpt-4-turbo-preview"

    def test_initialization_from_env(self):
        """Test initialization from environment variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            with patch("aurora_reasoning.llm_client.openai"):
                client = OpenAIClient()
                assert client._api_key == "env-key"

    @patch("aurora_reasoning.llm_client.openai")
    def test_generate(self, mock_openai):
        """Test generate method."""
        # Mock response
        mock_choice = MagicMock()
        mock_choice.message.content = "Generated response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4-turbo-preview"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.id = "chatcmpl-123"
        mock_response.created = 1234567890

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        client = OpenAIClient(api_key="test-key")
        response = client.generate("Test prompt")

        assert response.content == "Generated response"
        assert response.model == "gpt-4-turbo-preview"
        assert response.input_tokens == 10
        assert response.output_tokens == 5


class TestOllamaClient:
    """Test OllamaClient implementation."""

    def test_initialization(self):
        """Test initialization."""
        with patch("aurora_reasoning.llm_client.ollama"):
            client = OllamaClient()
            assert client._endpoint == "http://localhost:11434"
            assert client.default_model == "llama2"

    @patch("aurora_reasoning.llm_client.ollama")
    def test_generate(self, mock_ollama):
        """Test generate method."""
        # Mock response
        mock_response = {
            "message": {"content": "Generated response"},
            "model": "llama2",
            "done_reason": "stop",
            "total_duration": 1000000,
            "load_duration": 100000,
            "prompt_eval_count": 10,
            "eval_count": 5,
        }

        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        mock_ollama.Client.return_value = mock_client

        client = OllamaClient()
        response = client.generate("Test prompt")

        assert response.content == "Generated response"
        assert response.model == "llama2"
        assert response.finish_reason == "stop"
