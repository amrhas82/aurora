"""Unit tests for AURORA CLI configuration management.

Tests the dict-based config system:
- load_config() loads defaults + user overrides + env vars
- validate_config() checks types, ranges, and enum constraints
- Config class wraps dict with attribute accessors
"""

import json
import os

import pytest

from aurora_cli.config import (
    Config,
    load_config,
    validate_config,
)
from aurora_cli.errors import ConfigurationError


class TestLoadConfigDefaults:
    """Test load_config with default values."""

    def test_loads_defaults_when_no_file(self, tmp_path, monkeypatch):
        """load_config returns defaults.json values when no config file exists."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        config = load_config()

        assert config["version"] == "1.1.0"
        assert config["llm"]["provider"] == "anthropic"
        assert config["llm"]["temperature"] == 0.7
        assert config["storage"]["type"] == "sqlite"
        assert config["escalation"]["threshold"] == 0.7
        assert config["logging"]["level"] == "INFO"

    def test_loads_from_project_aurora_dir(self, tmp_path, monkeypatch):
        """load_config reads .aurora/config.json when .aurora/ exists."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        config_path = aurora_dir / "config.json"
        config_path.write_text(json.dumps({"llm": {"model": "custom-model"}}))

        monkeypatch.chdir(tmp_path)

        config = load_config()
        assert config["llm"]["model"] == "custom-model"
        # Defaults preserved for unspecified fields
        assert config["llm"]["provider"] == "anthropic"

    def test_loads_from_home_aurora_dir(self, tmp_path, monkeypatch):
        """load_config reads ~/.aurora/config.json when no local .aurora/."""
        home = tmp_path / "home"
        aurora_dir = home / ".aurora"
        aurora_dir.mkdir(parents=True)
        (aurora_dir / "config.json").write_text(
            json.dumps({"escalation": {"threshold": 0.9}})
        )

        monkeypatch.setenv("HOME", str(home))
        work = tmp_path / "work"
        work.mkdir()
        monkeypatch.chdir(work)

        config = load_config()
        assert config["escalation"]["threshold"] == 0.9

    def test_explicit_path(self, tmp_path):
        """load_config uses explicit path when provided."""
        cfg = tmp_path / "custom.json"
        cfg.write_text(json.dumps({"soar": {"default_model": "opus"}}))

        config = load_config(path=str(cfg))
        assert config["soar"]["default_model"] == "opus"

    def test_partial_file_merges_with_defaults(self, tmp_path, monkeypatch):
        """Partial config merges with defaults — missing fields get defaults."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        (aurora_dir / "config.json").write_text(
            json.dumps({"llm": {"model": "custom"}})
        )
        monkeypatch.chdir(tmp_path)

        config = load_config()
        assert config["llm"]["model"] == "custom"
        assert config["llm"]["max_tokens"] == 4096  # default preserved
        assert config["storage"]["max_connections"] == 10  # other section default


class TestLoadConfigEnvOverrides:
    """Test environment variable overrides."""

    def test_anthropic_api_key(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

        config = load_config()
        assert config["llm"]["api_key"] == "sk-test"

    def test_escalation_threshold(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AURORA_ESCALATION_THRESHOLD", "0.9")

        config = load_config()
        assert config["escalation"]["threshold"] == 0.9

    def test_invalid_escalation_threshold_raises(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AURORA_ESCALATION_THRESHOLD", "not_a_number")

        with pytest.raises(ConfigurationError, match="must be a number"):
            load_config()

    def test_logging_level_uppercased(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AURORA_LOGGING_LEVEL", "debug")

        config = load_config()
        assert config["logging"]["level"] == "DEBUG"

    def test_soar_model_valid(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AURORA_SOAR_MODEL", "opus")

        config = load_config()
        assert config["soar"]["default_model"] == "opus"

    def test_soar_model_invalid_raises(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AURORA_SOAR_MODEL", "gpt4")

        with pytest.raises(ConfigurationError, match="must be 'sonnet' or 'opus'"):
            load_config()

    def test_env_overrides_file(self, tmp_path, monkeypatch):
        """Env vars take precedence over config file values."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        (aurora_dir / "config.json").write_text(
            json.dumps({"escalation": {"threshold": 0.5}})
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AURORA_ESCALATION_THRESHOLD", "0.8")

        config = load_config()
        assert config["escalation"]["threshold"] == 0.8


class TestValidateConfig:
    """Test validate_config() for all config sections."""

    def test_valid_defaults_pass(self):
        """Default config from defaults.json passes validation."""
        import aurora_cli.config as cfg_mod
        with open(cfg_mod.DEFAULTS_FILE) as f:
            defaults = json.load(f)
        assert validate_config(defaults) == []

    # -- unknown sections --
    def test_unknown_section_reported(self):
        errors = validate_config({"unknown_section": {}})
        assert any("Unknown top-level" in e for e in errors)

    # -- storage --
    def test_storage_invalid_type(self):
        errors = validate_config({"storage": {"type": "postgres"}})
        assert any("storage.type" in e for e in errors)

    def test_storage_max_connections_not_positive(self):
        errors = validate_config({"storage": {"max_connections": 0}})
        assert any("storage.max_connections" in e for e in errors)

    def test_storage_timeout_negative(self):
        errors = validate_config({"storage": {"timeout_seconds": -1}})
        assert any("storage.timeout_seconds" in e for e in errors)

    # -- llm --
    def test_llm_invalid_provider(self):
        errors = validate_config({"llm": {"provider": "openai"}})
        assert any("llm.provider" in e for e in errors)

    def test_llm_temperature_out_of_range(self):
        errors = validate_config({"llm": {"temperature": 3.0}})
        assert any("llm.temperature" in e for e in errors)

    def test_llm_temperature_negative(self):
        errors = validate_config({"llm": {"temperature": -0.1}})
        assert any("llm.temperature" in e for e in errors)

    def test_llm_max_tokens_zero(self):
        errors = validate_config({"llm": {"max_tokens": 0}})
        assert any("llm.max_tokens" in e for e in errors)

    def test_llm_timeout_zero(self):
        errors = validate_config({"llm": {"timeout_seconds": 0}})
        assert any("llm.timeout_seconds" in e for e in errors)

    # -- escalation --
    def test_escalation_threshold_too_high(self):
        errors = validate_config({"escalation": {"threshold": 1.5}})
        assert any("escalation.threshold" in e for e in errors)

    def test_escalation_threshold_negative(self):
        errors = validate_config({"escalation": {"threshold": -0.1}})
        assert any("escalation.threshold" in e for e in errors)

    def test_escalation_invalid_force_mode(self):
        errors = validate_config({"escalation": {"force_mode": "invalid"}})
        assert any("force_mode" in e for e in errors)

    def test_escalation_null_force_mode_ok(self):
        errors = validate_config({"escalation": {"force_mode": None}})
        assert not any("force_mode" in e for e in errors)

    # -- logging --
    def test_logging_invalid_level(self):
        errors = validate_config({"logging": {"level": "TRACE"}})
        assert any("logging.level" in e for e in errors)

    def test_logging_max_size_mb_negative(self):
        errors = validate_config({"logging": {"max_size_mb": -1}})
        assert any("logging.max_size_mb" in e for e in errors)

    def test_logging_max_files_zero(self):
        errors = validate_config({"logging": {"max_files": 0}})
        assert any("logging.max_files" in e for e in errors)

    # -- search --
    def test_search_min_score_out_of_range(self):
        errors = validate_config({"search": {"min_semantic_score": 1.5}})
        assert any("search.min_semantic_score" in e for e in errors)

    # -- budget --
    def test_budget_limit_negative(self):
        errors = validate_config({"budget": {"limit": -1}})
        assert any("budget.limit" in e for e in errors)

    # -- soar --
    def test_soar_invalid_model(self):
        errors = validate_config({"soar": {"default_model": "gpt4"}})
        assert any("soar.default_model" in e for e in errors)

    # -- spawner --
    def test_spawner_max_concurrent_zero(self):
        errors = validate_config({"spawner": {"max_concurrent": 0}})
        assert any("spawner.max_concurrent" in e for e in errors)

    def test_spawner_stagger_delay_negative(self):
        errors = validate_config({"spawner": {"stagger_delay": -1}})
        assert any("spawner.stagger_delay" in e for e in errors)

    # -- memory --
    def test_memory_chunk_size_too_small(self):
        errors = validate_config({"memory": {"chunk_size": 50}})
        assert any("memory.chunk_size" in e for e in errors)

    def test_memory_overlap_negative(self):
        errors = validate_config({"memory": {"overlap": -1}})
        assert any("memory.overlap" in e for e in errors)

    # -- mcp --
    def test_mcp_max_results_zero(self):
        errors = validate_config({"mcp": {"max_results": 0}})
        assert any("mcp.max_results" in e for e in errors)

    # -- agents --
    def test_agents_refresh_interval_zero(self):
        errors = validate_config({"agents": {"refresh_interval_days": 0}})
        assert any("agents.refresh_interval_days" in e for e in errors)

    def test_agents_invalid_fallback_mode(self):
        errors = validate_config({"agents": {"fallback_mode": "magic"}})
        assert any("agents.fallback_mode" in e for e in errors)

    # -- context.code.hybrid_weights --
    def test_hybrid_weight_out_of_range(self):
        errors = validate_config({
            "context": {"code": {"hybrid_weights": {"activation": 1.5}}}
        })
        assert any("hybrid_weights.activation" in e for e in errors)

    def test_hybrid_top_k_zero(self):
        errors = validate_config({
            "context": {"code": {"hybrid_weights": {"top_k": 0}}}
        })
        assert any("hybrid_weights.top_k" in e for e in errors)

    def test_context_max_file_size_zero(self):
        errors = validate_config({"context": {"code": {"max_file_size_kb": 0}}})
        assert any("max_file_size_kb" in e for e in errors)

    # -- proactive_health_checks --
    def test_phc_check_interval_zero(self):
        errors = validate_config({"proactive_health_checks": {"check_interval": 0}})
        assert any("proactive_health_checks.check_interval" in e for e in errors)

    def test_phc_failure_threshold_zero(self):
        errors = validate_config({"proactive_health_checks": {"failure_threshold": 0}})
        assert any("proactive_health_checks.failure_threshold" in e for e in errors)

    # -- early_detection --
    def test_ed_stall_threshold_zero(self):
        errors = validate_config({"early_detection": {"stall_threshold": 0}})
        assert any("early_detection.stall_threshold" in e for e in errors)

    def test_ed_min_output_bytes_negative(self):
        errors = validate_config({"early_detection": {"min_output_bytes": -1}})
        assert any("early_detection.min_output_bytes" in e for e in errors)

    def test_ed_memory_limit_null_ok(self):
        errors = validate_config({"early_detection": {"memory_limit_mb": None}})
        assert not any("memory_limit_mb" in e for e in errors)

    def test_ed_memory_limit_negative(self):
        errors = validate_config({"early_detection": {"memory_limit_mb": -1}})
        assert any("early_detection.memory_limit_mb" in e for e in errors)

    # -- section not a dict --
    def test_section_not_dict(self):
        errors = validate_config({"storage": "not_a_dict"})
        assert any("storage must be a dict" in e for e in errors)

    # -- boundary values that should pass --
    def test_boundary_values_pass(self):
        config = {
            "escalation": {"threshold": 0.0},
            "llm": {"temperature": 0.0, "max_tokens": 1},
            "memory": {"chunk_size": 100, "overlap": 0},
            "mcp": {"max_results": 1},
            "budget": {"limit": 0},
            "spawner": {"max_concurrent": 1, "stagger_delay": 0},
        }
        errors = validate_config(config)
        assert errors == []

    def test_max_boundary_values_pass(self):
        config = {
            "escalation": {"threshold": 1.0},
            "llm": {"temperature": 2.0},
            "search": {"min_semantic_score": 1.0},
            "context": {"code": {"hybrid_weights": {"activation": 1.0, "semantic": 1.0}}},
        }
        errors = validate_config(config)
        assert errors == []

    def test_multiple_errors_accumulated(self):
        """validate_config accumulates all errors, not just the first."""
        config = {
            "llm": {"temperature": -1, "max_tokens": 0},
            "escalation": {"threshold": 5.0},
        }
        errors = validate_config(config)
        assert len(errors) >= 3


class TestConfigClass:
    """Test Config wrapper class."""

    def test_dict_access(self):
        config = Config()
        assert config["version"] == "1.1.0"
        assert config.get("nonexistent", "default") == "default"

    def test_property_accessors(self):
        config = Config()
        assert "aurora/memory.db" in config.db_path
        assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.search_min_semantic_score == 0.7
        assert config.budget_limit == 10.0
        assert config.soar_default_tool == "claude"
        assert config.soar_default_model == "sonnet"
        assert "aurora/plans" in config.planning_base_dir

    def test_validate_valid(self):
        config = Config()
        config.validate()  # should not raise

    def test_validate_invalid_raises(self):
        config = Config(data={"llm": {"temperature": -1}})
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_custom_data(self):
        config = Config(data={"version": "1.0.0", "soar": {"default_model": "opus"}})
        assert config.soar_default_model == "opus"

    def test_db_path_kwarg(self):
        config = Config(db_path="/custom/path.db")
        assert config.db_path == "/custom/path.db"

    def test_get_api_key_from_config(self):
        config = Config(data={"llm": {"api_key": "sk-test"}})
        assert config.get_api_key() == "sk-test"

    def test_get_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
        config = Config(data={"llm": {}})
        assert config.get_api_key() == "sk-env"
