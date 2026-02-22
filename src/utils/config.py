"""Configuration loader."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_config(name: str) -> dict:
    """Load a YAML config file from configs/ directory."""
    path = PROJECT_ROOT / "configs" / f"{name}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)
