"""Unit tests for LLM client interface and implementations."""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from aurora.reasoning.llm_client import (
    AnthropicClient,
    LLMResponse,
    OllamaClient,
    OpenAIClient,
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
        text = """Here is the result:
```json
{"key": "value"}
```
Hope this helps!"""
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_json_in_code_block_no_language(self):
        """Test extracting JSON from code block without language specifier."""
        text = """```
{"key": "value"}
```"""
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

    @pytest.fixture
    def mock_anthropic_module(self):
        """Create a mock anthropic module."""
        # Create mock module and add to sys.modules before import
        mock_module = MagicMock()

        # Mock the Anthropic class
        mock_client_instance = MagicMock()
        mock_module.Anthropic.return_value = mock_client_instance

        with patch.dict("sys.modules", {"anthropic": mock_module}):
            yield mock_module, mock_client_instance

    def test_initialization_with_api_key(self, mock_anthropic_module):
        """Test initialization with explicit API key."""
        _, _ = mock_anthropic_module
        client = AnthropicClient(api_key="test-key")
        assert client._api_key == "test-key"
        assert client.default_model == "claude-sonnet-4-20250514"

    def test_initialization_from_env(self, mock_anthropic_module):
        """Test initialization from environment variable."""
        _, _ = mock_anthropic_module
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            client = AnthropicClient()
            assert client._api_key == "env-key"

    def test_initialization_no_api_key(self):
        """Test error when no API key provided."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key required"):
                AnthropicClient()

    def test_initialization_missing_anthropic_library(self):
        """Test error when anthropic library not installed."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            # Temporarily remove anthropic from sys.modules if it exists
            original = sys.modules.get("anthropic")
            if "anthropic" in sys.modules:
                del sys.modules["anthropic"]

            try:
                # Make import raise ImportError
                with patch.dict("sys.modules", {"anthropic": None}):
                    with pytest.raises(ImportError, match="anthropic package required"):
                        # Force a reload of the module to trigger the import
                        import importlib

                        import aurora.reasoning.llm_client as llm_module
                        importlib.reload(llm_module)
                        llm_module.AnthropicClient()
            finally:
                # Restore original state
                if original is not None:
                    sys.modules["anthropic"] = original

    def test_custom_default_model(self, mock_anthropic_module):
        """Test initialization with custom default model."""
        _, _ = mock_anthropic_module
        client = AnthropicClient(api_key="test-key", default_model="claude-opus-4")
        assert client.default_model == "claude-opus-4"

    def test_generate(self, mock_anthropic_module):
        """Test generate method."""
        mock_module, mock_client_instance = mock_anthropic_module

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated response")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client_instance.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        response = client.generate("Test prompt")

        assert response.content == "Generated response"
        assert response.model == "claude-sonnet-4-20250514"
        assert response.input_tokens == 10
        assert response.output_tokens == 5
        assert response.finish_reason == "end_turn"

    def test_generate_with_system_prompt(self, mock_anthropic_module):
        """Test generate with system prompt."""
        mock_module, mock_client_instance = mock_anthropic_module

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 3
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client_instance.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        response = client.generate("Test prompt", system="You are helpful")

        mock_client_instance.messages.create.assert_called_once()
        call_kwargs = mock_client_instance.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful"

    def test_generate_with_custom_params(self, mock_anthropic_module):
        """Test generate with custom temperature and max_tokens."""
        mock_module, mock_client_instance = mock_anthropic_module

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 3
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client_instance.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        response = client.generate("Test prompt", max_tokens=2048, temperature=0.5)

        call_kwargs = mock_client_instance.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.5

    def test_generate_empty_prompt(self, mock_anthropic_module):
        """Test error on empty prompt."""
        _, _ = mock_anthropic_module
        client = AnthropicClient(api_key="test-key")

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate("")

    def test_generate_whitespace_prompt(self, mock_anthropic_module):
        """Test error on whitespace-only prompt."""
        _, _ = mock_anthropic_module
        client = AnthropicClient(api_key="test-key")

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate("   ")

    def test_generate_api_failure(self, mock_anthropic_module):
        """Test error handling on API failure."""
        mock_module, mock_client_instance = mock_anthropic_module

        mock_client_instance.messages.create.side_effect = Exception("API error")

        client = AnthropicClient(api_key="test-key")

        with pytest.raises(RuntimeError, match="Anthropic API call failed"):
            client.generate("Test prompt")

    def test_generate_json(self, mock_anthropic_module):
        """Test generate_json method."""
        mock_module, mock_client_instance = mock_anthropic_module

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"result": "success"}')]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client_instance.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        result = client.generate_json("Test prompt")

        assert result == {"result": "success"}

    def test_generate_json_with_markdown(self, mock_anthropic_module):
        """Test generate_json extracts JSON from markdown."""
        mock_module, mock_client_instance = mock_anthropic_module

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"result": "success"}\n```')]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client_instance.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        result = client.generate_json("Test prompt")

        assert result == {"result": "success"}

    def test_generate_json_invalid_response(self, mock_anthropic_module):
        """Test generate_json with invalid JSON response."""
        mock_module, mock_client_instance = mock_anthropic_module

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Not JSON at all")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client_instance.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")

        with pytest.raises(ValueError, match="Failed to extract JSON"):
            client.generate_json("Test prompt")

    def test_generate_json_enhances_system_prompt(self, mock_anthropic_module):
        """Test that generate_json enhances system prompt to enforce JSON."""
        mock_module, mock_client_instance = mock_anthropic_module

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"result": "success"}')]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client_instance.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        client.generate_json("Test prompt", system="Be helpful")

        call_kwargs = mock_client_instance.messages.create.call_args[1]
        assert "Be helpful" in call_kwargs["system"]
        assert "valid JSON only" in call_kwargs["system"]

    def test_count_tokens(self, mock_anthropic_module):
        """Test token counting."""
        _, _ = mock_anthropic_module
        client = AnthropicClient(api_key="test-key")
        tokens = client.count_tokens("This is a test")
        assert tokens == len("This is a test") // 4

    @patch("aurora.reasoning.llm_client.time")
    def test_rate_limiting(self, mock_time, mock_anthropic_module):
        """Test rate limiting between requests."""
        mock_module, mock_client_instance = mock_anthropic_module

        # Use infinite iterator for time.time() to avoid StopIteration
        def time_generator():
            times = iter([0.0, 0.0, 0.05, 0.05, 0.15, 0.15, 0.25, 0.25])
            while True:
                try:
                    yield next(times)
                except StopIteration:
                    yield 1.0  # Default value after sequence exhausted

        mock_time.time.side_effect = time_generator()
        mock_time.sleep = MagicMock()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.stop_sequence = None

        mock_client_instance.messages.create.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        client.generate("First prompt")
        client.generate("Second prompt")

        # Should have slept because second call was too soon
        # The sleep function is called at least once to enforce rate limiting
        assert mock_time.sleep.call_count >= 1


class TestOpenAIClient:
    """Test OpenAIClient implementation."""

    @pytest.fixture
    def mock_openai_module(self):
        """Create a mock openai module."""
        mock_module = MagicMock()
        mock_client_instance = MagicMock()
        mock_module.OpenAI.return_value = mock_client_instance

        with patch.dict("sys.modules", {"openai": mock_module}):
            yield mock_module, mock_client_instance

    def test_initialization_with_api_key(self, mock_openai_module):
        """Test initialization with explicit API key."""
        _, _ = mock_openai_module
        client = OpenAIClient(api_key="test-key")
        assert client._api_key == "test-key"
        assert client.default_model == "gpt-4-turbo-preview"

    def test_initialization_from_env(self, mock_openai_module):
        """Test initialization from environment variable."""
        _, _ = mock_openai_module
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            client = OpenAIClient()
            assert client._api_key == "env-key"

    def test_initialization_no_api_key(self):
        """Test error when no API key provided."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key required"):
                OpenAIClient()

    def test_custom_default_model(self, mock_openai_module):
        """Test initialization with custom default model."""
        _, _ = mock_openai_module
        client = OpenAIClient(api_key="test-key", default_model="gpt-4")
        assert client.default_model == "gpt-4"

    def test_generate(self, mock_openai_module):
        """Test generate method."""
        mock_module, mock_client_instance = mock_openai_module

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

        mock_client_instance.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        response = client.generate("Test prompt")

        assert response.content == "Generated response"
        assert response.model == "gpt-4-turbo-preview"
        assert response.input_tokens == 10
        assert response.output_tokens == 5

    def test_generate_with_system_prompt(self, mock_openai_module):
        """Test generate with system prompt."""
        mock_module, mock_client_instance = mock_openai_module

        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4-turbo-preview"
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 3
        mock_response.id = "chatcmpl-123"
        mock_response.created = 1234567890

        mock_client_instance.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        response = client.generate("Test prompt", system="You are helpful")

        mock_client_instance.chat.completions.create.assert_called_once()
        call_kwargs = mock_client_instance.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"

    def test_generate_empty_prompt(self, mock_openai_module):
        """Test error on empty prompt."""
        _, _ = mock_openai_module
        client = OpenAIClient(api_key="test-key")

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate("")

    def test_generate_api_failure(self, mock_openai_module):
        """Test error handling on API failure."""
        mock_module, mock_client_instance = mock_openai_module

        mock_client_instance.chat.completions.create.side_effect = Exception("API error")

        client = OpenAIClient(api_key="test-key")

        with pytest.raises(RuntimeError, match="OpenAI API call failed"):
            client.generate("Test prompt")

    def test_generate_json(self, mock_openai_module):
        """Test generate_json method."""
        mock_module, mock_client_instance = mock_openai_module

        mock_choice = MagicMock()
        mock_choice.message.content = '{"result": "success"}'
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4-turbo-preview"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.id = "chatcmpl-123"
        mock_response.created = 1234567890

        mock_client_instance.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        result = client.generate_json("Test prompt")

        assert result == {"result": "success"}

    def test_generate_json_with_response_format(self, mock_openai_module):
        """Test that generate_json sets response_format for JSON mode."""
        mock_module, mock_client_instance = mock_openai_module

        mock_choice = MagicMock()
        mock_choice.message.content = '{"result": "success"}'
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4-turbo-preview"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.id = "chatcmpl-123"
        mock_response.created = 1234567890

        mock_client_instance.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        client.generate_json("Test prompt")

        call_kwargs = mock_client_instance.chat.completions.create.call_args[1]
        assert "response_format" in call_kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_generate_no_usage_tokens(self, mock_openai_module):
        """Test generate with response that has no usage info."""
        mock_module, mock_client_instance = mock_openai_module

        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4-turbo-preview"
        mock_response.usage = None  # No usage info
        mock_response.id = "chatcmpl-123"
        mock_response.created = 1234567890

        mock_client_instance.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        response = client.generate("Test prompt")

        assert response.input_tokens == 0
        assert response.output_tokens == 0

    def test_count_tokens(self, mock_openai_module):
        """Test token counting."""
        _, _ = mock_openai_module
        client = OpenAIClient(api_key="test-key")
        tokens = client.count_tokens("This is a test")
        assert tokens == len("This is a test") // 4


class TestOllamaClient:
    """Test OllamaClient implementation."""

    @pytest.fixture
    def mock_ollama_module(self):
        """Create a mock ollama module."""
        mock_module = MagicMock()
        mock_client_instance = MagicMock()
        mock_module.Client.return_value = mock_client_instance

        with patch.dict("sys.modules", {"ollama": mock_module}):
            yield mock_module, mock_client_instance

    def test_initialization(self, mock_ollama_module):
        """Test initialization."""
        _, _ = mock_ollama_module
        client = OllamaClient()
        assert client._endpoint == "http://localhost:11434"
        assert client.default_model == "llama2"

    def test_initialization_custom_endpoint(self, mock_ollama_module):
        """Test initialization with custom endpoint."""
        _, _ = mock_ollama_module
        client = OllamaClient(endpoint="http://custom:8080", default_model="mistral")
        assert client._endpoint == "http://custom:8080"
        assert client.default_model == "mistral"

    def test_generate(self, mock_ollama_module):
        """Test generate method."""
        mock_module, mock_client_instance = mock_ollama_module

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

        mock_client_instance.chat.return_value = mock_response

        client = OllamaClient()
        response = client.generate("Test prompt")

        assert response.content == "Generated response"
        assert response.model == "llama2"
        assert response.finish_reason == "stop"

    def test_generate_with_system_prompt(self, mock_ollama_module):
        """Test generate with system prompt."""
        mock_module, mock_client_instance = mock_ollama_module

        mock_response = {
            "message": {"content": "Response"},
            "model": "llama2",
            "done_reason": "stop",
        }

        mock_client_instance.chat.return_value = mock_response

        client = OllamaClient()
        response = client.generate("Test prompt", system="You are helpful")

        mock_client_instance.chat.assert_called_once()
        call_kwargs = mock_client_instance.chat.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"

    def test_generate_empty_prompt(self, mock_ollama_module):
        """Test error on empty prompt."""
        _, _ = mock_ollama_module
        client = OllamaClient()

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate("")

    def test_generate_api_failure(self, mock_ollama_module):
        """Test error handling on API failure."""
        mock_module, mock_client_instance = mock_ollama_module

        mock_client_instance.chat.side_effect = Exception("Connection error")

        client = OllamaClient()

        with pytest.raises(RuntimeError, match="Ollama API call failed"):
            client.generate("Test prompt")

    def test_generate_json(self, mock_ollama_module):
        """Test generate_json method."""
        mock_module, mock_client_instance = mock_ollama_module

        mock_response = {
            "message": {"content": '{"result": "success"}'},
            "model": "llama2",
            "done_reason": "stop",
        }

        mock_client_instance.chat.return_value = mock_response

        client = OllamaClient()
        result = client.generate_json("Test prompt")

        assert result == {"result": "success"}

    def test_generate_with_custom_options(self, mock_ollama_module):
        """Test generate with custom options."""
        mock_module, mock_client_instance = mock_ollama_module

        mock_response = {
            "message": {"content": "Response"},
            "model": "llama2",
            "done_reason": "stop",
        }

        mock_client_instance.chat.return_value = mock_response

        client = OllamaClient()
        response = client.generate("Test prompt", max_tokens=2048, temperature=0.5)

        call_kwargs = mock_client_instance.chat.call_args[1]
        options = call_kwargs["options"]
        assert options["temperature"] == 0.5
        assert options["num_predict"] == 2048

    def test_generate_estimates_tokens(self, mock_ollama_module):
        """Test that token counts are estimated when not provided."""
        mock_module, mock_client_instance = mock_ollama_module

        mock_response = {
            "message": {"content": "Test response"},
            "model": "llama2",
            "done_reason": "stop",
        }

        mock_client_instance.chat.return_value = mock_response

        client = OllamaClient()
        response = client.generate("Test prompt")

        # Tokens should be estimated using heuristic
        assert response.input_tokens > 0
        assert response.output_tokens > 0

    def test_count_tokens(self, mock_ollama_module):
        """Test token counting."""
        _, _ = mock_ollama_module
        client = OllamaClient()
        tokens = client.count_tokens("This is a test")
        assert tokens == len("This is a test") // 4
