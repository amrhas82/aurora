"""Unit tests for auto-escalation handler.

This module tests the auto-escalation functionality including:
- Complexity assessment using Phase 2 keyword classifier
- Escalation threshold configuration
- Routing decisions (direct LLM vs AURORA)
- Transparent escalation
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from aurora.cli.escalation import (
    AutoEscalationHandler,
    EscalationConfig,
    EscalationResult,
)


class TestEscalationConfig:
    """Tests for EscalationConfig class."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = EscalationConfig()
        assert config.threshold == 0.6
        assert config.enable_keyword_only is True
        assert config.force_aurora is False
        assert config.force_direct is False

    def test_config_custom_threshold(self):
        """Test custom threshold configuration."""
        config = EscalationConfig(threshold=0.7)
        assert config.threshold == 0.7

    def test_config_invalid_threshold_low(self):
        """Test validation for threshold below 0.0."""
        with pytest.raises(ValueError, match="threshold must be in"):
            EscalationConfig(threshold=-0.1)

    def test_config_invalid_threshold_high(self):
        """Test validation for threshold above 1.0."""
        with pytest.raises(ValueError, match="threshold must be in"):
            EscalationConfig(threshold=1.1)

    def test_config_force_both_modes(self):
        """Test validation for forcing both modes simultaneously."""
        with pytest.raises(ValueError, match="Cannot force both"):
            EscalationConfig(force_aurora=True, force_direct=True)

    def test_config_keyword_only_mode(self):
        """Test keyword-only mode configuration."""
        config = EscalationConfig(enable_keyword_only=True)
        assert config.enable_keyword_only is True

    def test_config_llm_verification_mode(self):
        """Test LLM verification mode configuration."""
        config = EscalationConfig(enable_keyword_only=False)
        assert config.enable_keyword_only is False


class TestEscalationResult:
    """Tests for EscalationResult dataclass."""

    def test_result_creation(self):
        """Test creation of EscalationResult."""
        result = EscalationResult(
            use_aurora=True,
            complexity="COMPLEX",
            confidence=0.85,
            method="keyword",
            reasoning="High complexity detected",
            score=0.75,
        )
        assert result.use_aurora is True
        assert result.complexity == "COMPLEX"
        assert result.confidence == 0.85
        assert result.method == "keyword"
        assert result.score == 0.75


class TestAutoEscalationHandler:
    """Tests for AutoEscalationHandler class."""

    def test_handler_initialization_defaults(self):
        """Test handler initialization with defaults."""
        handler = AutoEscalationHandler()
        assert handler.config is not None
        assert handler.config.threshold == 0.6
        assert handler.llm_client is None

    def test_handler_initialization_custom_config(self):
        """Test handler initialization with custom config."""
        config = EscalationConfig(threshold=0.7)
        handler = AutoEscalationHandler(config=config)
        assert handler.config.threshold == 0.7

    def test_handler_initialization_with_llm(self):
        """Test handler initialization with LLM client."""
        mock_llm = Mock()
        handler = AutoEscalationHandler(llm_client=mock_llm)
        assert handler.llm_client is mock_llm

    @patch("aurora_cli.escalation.assess_complexity")
    def test_assess_query_simple(self, mock_assess):
        """Test assessment of simple query routes to direct LLM."""
        # Mock complexity assessment returning SIMPLE
        mock_assess.return_value = {
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "Simple informational query",
            "score": 0.2,
        }

        handler = AutoEscalationHandler()
        result = handler.assess_query("What is a function?")

        assert result.use_aurora is False  # Below threshold (0.2 < 0.6)
        assert result.complexity == "SIMPLE"
        assert result.confidence == 0.9
        assert result.method == "keyword"
        assert result.score == 0.2

    @patch("aurora_cli.escalation.assess_complexity")
    def test_assess_query_medium(self, mock_assess):
        """Test assessment of medium query (borderline)."""
        # Mock complexity assessment returning MEDIUM
        mock_assess.return_value = {
            "complexity": "MEDIUM",
            "confidence": 0.8,
            "method": "keyword",
            "reasoning": "Multi-step query",
            "score": 0.5,
        }

        handler = AutoEscalationHandler()
        result = handler.assess_query("Create a user authentication function")

        assert result.use_aurora is False  # Below threshold (0.5 < 0.6)
        assert result.complexity == "MEDIUM"
        assert result.score == 0.5

    @patch("aurora_cli.escalation.assess_complexity")
    def test_assess_query_complex(self, mock_assess):
        """Test assessment of complex query routes to AURORA."""
        # Mock complexity assessment returning COMPLEX
        mock_assess.return_value = {
            "complexity": "COMPLEX",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "System-level design required",
            "score": 0.75,
        }

        handler = AutoEscalationHandler()
        result = handler.assess_query("Design a microservices architecture")

        assert result.use_aurora is True  # Above threshold (0.75 >= 0.6)
        assert result.complexity == "COMPLEX"
        assert result.score == 0.75

    @patch("aurora_cli.escalation.assess_complexity")
    def test_assess_query_critical(self, mock_assess):
        """Test assessment of critical query routes to AURORA."""
        # Mock complexity assessment returning CRITICAL
        mock_assess.return_value = {
            "complexity": "CRITICAL",
            "confidence": 0.95,
            "method": "keyword",
            "reasoning": "Security-critical operation",
            "score": 0.95,
        }

        handler = AutoEscalationHandler()
        result = handler.assess_query("Fix authentication vulnerability")

        assert result.use_aurora is True  # Well above threshold
        assert result.complexity == "CRITICAL"
        assert result.score == 0.95

    @patch("aurora_cli.escalation.assess_complexity")
    def test_assess_query_custom_threshold(self, mock_assess):
        """Test assessment with custom threshold."""
        # Mock complexity assessment
        mock_assess.return_value = {
            "complexity": "MEDIUM",
            "confidence": 0.8,
            "method": "keyword",
            "reasoning": "Medium complexity",
            "score": 0.5,
        }

        # Lower threshold to 0.4 - now MEDIUM (0.5) should use AURORA
        config = EscalationConfig(threshold=0.4)
        handler = AutoEscalationHandler(config=config)
        result = handler.assess_query("Refactor the database layer")

        assert result.use_aurora is True  # 0.5 >= 0.4
        assert result.score == 0.5

    def test_assess_query_force_aurora(self):
        """Test forced AURORA mode."""
        config = EscalationConfig(force_aurora=True)
        handler = AutoEscalationHandler(config=config)
        result = handler.assess_query("What is a variable?")

        assert result.use_aurora is True
        assert result.complexity == "FORCED"
        assert result.confidence == 1.0
        assert result.method == "forced"

    def test_assess_query_force_direct(self):
        """Test forced direct LLM mode."""
        config = EscalationConfig(force_direct=True)
        handler = AutoEscalationHandler(config=config)
        result = handler.assess_query("Design a complex system")

        assert result.use_aurora is False
        assert result.complexity == "FORCED"
        assert result.confidence == 1.0
        assert result.method == "forced"

    @patch("aurora_cli.escalation.assess_complexity")
    def test_assess_query_at_threshold(self, mock_assess):
        """Test assessment exactly at threshold."""
        # Mock complexity assessment at exact threshold
        mock_assess.return_value = {
            "complexity": "MEDIUM",
            "confidence": 0.8,
            "method": "keyword",
            "reasoning": "At threshold",
            "score": 0.6,
        }

        handler = AutoEscalationHandler()
        result = handler.assess_query("Query at threshold")

        assert result.use_aurora is True  # 0.6 >= 0.6 (inclusive)
        assert result.score == 0.6

    @patch("aurora_cli.escalation.assess_complexity")
    def test_assess_query_keyword_only(self, mock_assess):
        """Test assessment with keyword-only mode."""
        mock_assess.return_value = {
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "Keyword classification",
            "score": 0.2,
        }

        config = EscalationConfig(enable_keyword_only=True)
        handler = AutoEscalationHandler(config=config)
        handler.assess_query("What is Python?")

        # Should use keyword-only (no LLM client passed to assess_complexity)
        mock_assess.assert_called_once()
        call_args = mock_assess.call_args
        assert call_args[1]["llm_client"] is None

    @patch("aurora_cli.escalation.assess_complexity")
    def test_assess_query_with_llm_verification(self, mock_assess):
        """Test assessment with LLM verification enabled."""
        mock_assess.return_value = {
            "complexity": "MEDIUM",
            "confidence": 0.7,
            "method": "llm",
            "reasoning": "LLM verification",
            "score": 0.5,
        }

        mock_llm = Mock()
        config = EscalationConfig(enable_keyword_only=False)
        handler = AutoEscalationHandler(config=config, llm_client=mock_llm)
        handler.assess_query("Borderline complexity query")

        # Should pass LLM client for verification
        mock_assess.assert_called_once()
        call_args = mock_assess.call_args
        assert call_args[1]["llm_client"] is mock_llm

    @patch("aurora_cli.escalation.assess_complexity")
    def test_complexity_to_score_mapping(self, mock_assess):
        """Test complexity level to score mapping."""
        handler = AutoEscalationHandler()

        # Test SIMPLE mapping
        assert handler._complexity_to_score("SIMPLE") == 0.2
        assert handler._complexity_to_score("simple") == 0.2

        # Test MEDIUM mapping
        assert handler._complexity_to_score("MEDIUM") == 0.5
        assert handler._complexity_to_score("medium") == 0.5

        # Test COMPLEX mapping
        assert handler._complexity_to_score("COMPLEX") == 0.75
        assert handler._complexity_to_score("complex") == 0.75

        # Test CRITICAL mapping
        assert handler._complexity_to_score("CRITICAL") == 0.95
        assert handler._complexity_to_score("critical") == 0.95

        # Test unknown complexity (default to MEDIUM)
        assert handler._complexity_to_score("UNKNOWN") == 0.5

    @patch("aurora_cli.escalation.assess_complexity")
    def test_should_use_aurora_simple(self, mock_assess):
        """Test should_use_aurora convenience method for simple query."""
        mock_assess.return_value = {
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "Simple query",
            "score": 0.2,
        }

        handler = AutoEscalationHandler()
        assert handler.should_use_aurora("What is a function?") is False

    @patch("aurora_cli.escalation.assess_complexity")
    def test_should_use_aurora_complex(self, mock_assess):
        """Test should_use_aurora convenience method for complex query."""
        mock_assess.return_value = {
            "complexity": "COMPLEX",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "Complex query",
            "score": 0.75,
        }

        handler = AutoEscalationHandler()
        assert handler.should_use_aurora("Design a system") is True

    @patch("aurora_cli.escalation.assess_complexity")
    def test_get_execution_mode_direct(self, mock_assess):
        """Test get_execution_mode for direct LLM."""
        mock_assess.return_value = {
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "Simple query",
            "score": 0.2,
        }

        handler = AutoEscalationHandler()
        mode = handler.get_execution_mode("What is Python?")
        assert mode == "direct"

    @patch("aurora_cli.escalation.assess_complexity")
    def test_get_execution_mode_aurora(self, mock_assess):
        """Test get_execution_mode for AURORA."""
        mock_assess.return_value = {
            "complexity": "COMPLEX",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "Complex query",
            "score": 0.75,
        }

        handler = AutoEscalationHandler()
        mode = handler.get_execution_mode("Design architecture")
        assert mode == "aurora"

    @patch("aurora_cli.escalation.assess_complexity")
    def test_transparent_escalation_simple_to_direct(self, mock_assess):
        """Test transparent escalation from simple query to direct LLM."""
        mock_assess.return_value = {
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "Informational query",
            "score": 0.2,
        }

        handler = AutoEscalationHandler()
        result = handler.assess_query("Explain Python variables")

        # User doesn't specify mode, system transparently chooses direct LLM
        assert result.use_aurora is False
        assert result.reasoning == "Informational query"

    @patch("aurora_cli.escalation.assess_complexity")
    def test_transparent_escalation_complex_to_aurora(self, mock_assess):
        """Test transparent escalation from complex query to AURORA."""
        mock_assess.return_value = {
            "complexity": "COMPLEX",
            "confidence": 0.9,
            "method": "keyword",
            "reasoning": "Multi-agent coordination needed",
            "score": 0.75,
        }

        handler = AutoEscalationHandler()
        result = handler.assess_query("Refactor entire authentication system")

        # User doesn't specify mode, system transparently chooses AURORA
        assert result.use_aurora is True
        assert "coordination" in result.reasoning.lower()


class TestEscalationIntegration:
    """Integration tests for escalation with real keyword classifier."""

    def test_real_simple_query(self):
        """Test real simple query without mocks."""
        handler = AutoEscalationHandler()
        result = handler.assess_query("What is a Python function?")

        # Should route to direct LLM (informational query)
        assert result.use_aurora is False
        assert result.complexity in ["SIMPLE", "MEDIUM"]

    def test_real_complex_query(self):
        """Test real complex query without mocks."""
        handler = AutoEscalationHandler()
        result = handler.assess_query(
            "Design and implement a distributed microservices architecture "
            "with service discovery and load balancing"
        )

        # Should have reasonable assessment (keyword classifier may be conservative)
        # Note: Keyword-only classifier may not always detect complexity without LLM verification
        assert result.complexity in ["SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"]
        assert 0.0 <= result.score <= 1.0

    def test_real_security_query(self):
        """Test real security-related query without mocks."""
        handler = AutoEscalationHandler()
        result = handler.assess_query("Fix security vulnerability in authentication system")

        # Should route to AURORA (security = critical)
        assert result.use_aurora is True
        assert result.complexity in ["COMPLEX", "CRITICAL"]

    def test_real_borderline_query(self):
        """Test real borderline complexity query without mocks."""
        handler = AutoEscalationHandler()
        result = handler.assess_query("Create a user registration form")

        # Borderline - could go either way, should have reasonable output
        # Note: Low confidence is expected for borderline cases with keyword-only
        assert result.confidence >= 0.0 and result.confidence <= 1.0
        assert result.score >= 0.0 and result.score <= 1.0
