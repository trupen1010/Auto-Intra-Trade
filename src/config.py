"""Configuration loading utilities."""

from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from src.models.config_models import AppConfig
from src.utils.exceptions import ConfigValidationError


def _parse_hhmm(value: str, field_name: str) -> time:
    """Parse a HH:MM time string.

    Args:
        value: Time value in HH:MM format.
        field_name: Config field name for error messages.

    Returns:
        Parsed time value.

    Raises:
        ConfigValidationError: If parsing fails.
    """
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        msg = f"Invalid time format for '{field_name}'; expected HH:MM."
        raise ConfigValidationError(msg) from exc


def load_config(path: Path | str = "config/settings.yaml") -> AppConfig:
    """Load and validate application configuration from YAML.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        A newly validated AppConfig instance.

    Raises:
        ConfigValidationError: If the file cannot be parsed or validated.
    """
    config_path = Path(path)

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            loaded_config: Any = yaml.safe_load(config_file)
    except (OSError, yaml.YAMLError) as exc:
        msg = f"Failed to read config from '{config_path}'."
        raise ConfigValidationError(msg) from exc

    config_data: dict[str, Any] = loaded_config or {}
    if not isinstance(config_data, dict):
        msg = f"Configuration root in '{config_path}' must be a YAML mapping."
        raise ConfigValidationError(msg)

    execution_data = config_data.get("execution")
    if isinstance(execution_data, dict):
        for field_name in ("entry_cutoff_time", "forced_exit_time"):
            field_value = execution_data.get(field_name)
            if isinstance(field_value, str):
                execution_data[field_name] = _parse_hhmm(field_value, field_name)

    try:
        return AppConfig.model_validate(config_data)
    except ValidationError as exc:
        msg = f"Configuration validation failed for '{config_path}'."
        raise ConfigValidationError(msg) from exc
