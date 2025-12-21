# AURORA Reasoning Package

Reasoning and LLM integration components for the AURORA framework.

## Features

- Abstract LLM client interface with multi-provider support
- Anthropic Claude integration
- OpenAI GPT integration
- Ollama local model integration
- Prompt template system with few-shot learning
- Query decomposition logic
- Multi-stage verification (self-verification and adversarial)
- Result synthesis with traceability

## Installation

```bash
pip install -e packages/reasoning
```

## Configuration

Set environment variables for API keys:

```bash
export ANTHROPIC_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
```

## Usage

```python
from aurora_reasoning.llm_client import AnthropicClient

client = AnthropicClient()
response = client.generate("What is the capital of France?")
```

## License

MIT
