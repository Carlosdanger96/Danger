"""
Configuration management for Project DEGENERATE.

Loads settings from config.yaml and environment variables.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AccountConfig(BaseModel):
    starting_equity: float = 100000.0
    hard_floor: float = 30000.0
    max_drawdown: float = 0.70


class SleeveConfig(BaseModel):
    allocation: float
    enabled: bool = True


class SleevesConfig(BaseModel):
    wsb: SleeveConfig = Field(default_factory=lambda: SleeveConfig(allocation=0.25))
    pelosi: SleeveConfig = Field(default_factory=lambda: SleeveConfig(allocation=0.25))
    inverse_cramer: SleeveConfig = Field(
        default_factory=lambda: SleeveConfig(allocation=0.50)
    )


class OptionsConfig(BaseModel):
    min_dte: int = 3
    max_dte: int = 45
    preferred_delta_min: float = 0.10
    preferred_delta_max: float = 0.40
    absurd_delta_min: float = 0.05
    absurd_delta_max: float = 0.15
    prefer_otm: bool = True
    max_premium_percent: float = 0.10


class TierConfig(BaseModel):
    delta_min: float
    delta_max: float
    dte_min: int
    dte_max: int
    weight: float


class StrategyConfig(BaseModel):
    consensus: dict[str, float] = Field(
        default_factory=lambda: {"one_source": 1.0, "two_sources": 1.5, "three_sources": 2.0}
    )
    signal_thresholds: dict[str, float] = Field(
        default_factory=lambda: {"minimum": 0.75, "extreme": 0.90}
    )
    sizing: dict[str, float] = Field(
        default_factory=lambda: {"low": 0.05, "normal": 0.10, "high": 0.20, "extreme": 0.30}
    )
    contract_tiers: dict[str, TierConfig] = Field(default_factory=dict)
    desperation: dict[str, Any] = Field(default_factory=dict)


class ExecutionConfig(BaseModel):
    paper_only: bool = True
    max_order_size: float = 50000.0
    max_position_size: float = 100000.0


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "data/degenerate.log"
    db_path: str = "data/trades.db"


class MarketConfig(BaseModel):
    open_time: str = "09:30"
    close_time: str = "16:00"
    timezone: str = "America/New_York"


class WSBConfig(BaseModel):
    subreddit: str = "wallstreetbets"
    lookback_minutes: int = 60
    acceleration_window: int = 15
    meme_terms: list[str] = Field(default_factory=list)


class PelosiConfig(BaseModel):
    api_url: str = "https://disclosures.clerk.house.gov"
    lookback_days: int = 30


class CramerConfig(BaseModel):
    enabled: bool = True
    classification_model: str = "gpt-4o-mini"
    confidence_threshold: float = 0.85


class SignalSourcesConfig(BaseModel):
    wsb: WSBConfig = Field(default_factory=WSBConfig)
    pelosi: PelosiConfig = Field(default_factory=PelosiConfig)
    cramer: CramerConfig = Field(default_factory=CramerConfig)


class AppConfig(BaseModel):
    account: AccountConfig = Field(default_factory=AccountConfig)
    sleeves: SleevesConfig = Field(default_factory=SleevesConfig)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    market: MarketConfig = Field(default_factory=MarketConfig)
    signal_sources: SignalSourcesConfig = Field(default_factory=SignalSourcesConfig)


class Settings(BaseSettings):
    """Environment variable settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_paper: bool = True
    openai_api_key: str = ""
    database_path: str = "data/trades.db"
    log_level: str = "INFO"
    log_file: str = "data/degenerate.log"


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """
    Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to config.yaml. If None, uses default locations.
        
    Returns:
        AppConfig instance with merged settings.
    """
    # Default config paths
    if config_path is None:
        search_paths = [
            Path(__file__).parent.parent / "config.yaml",
            Path.cwd() / "config.yaml",
            Path("/etc/project-degenerate/config.yaml"),
        ]
        for path in search_paths:
            if path.exists():
                config_path = path
                break
        else:
            raise FileNotFoundError(
                "config.yaml not found in expected locations. "
                "Please create one or specify the path."
            )
    
    config_path = Path(config_path)
    
    # Load YAML config
    with open(config_path) as f:
        yaml_config = yaml.safe_load(f)
    
    # Convert nested dicts to models
    app_config = AppConfig(**yaml_config)
    
    # Override with environment variables
    settings = Settings()
    
    # Merge environment overrides
    if settings.alpaca_api_key:
        # Environment takes precedence
        pass  # Alpaca config is handled separately
    
    return app_config


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return load_config()


# Global config instance (lazy loaded)
_config: AppConfig | None = None


def init_config(config_path: str | Path | None = None) -> AppConfig:
    """Initialize and return the global configuration."""
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def get_alpaca_config() -> dict[str, Any]:
    """Get Alpaca-specific configuration from environment."""
    settings = Settings()
    return {
        "api_key": settings.alpaca_api_key,
        "api_secret": settings.alpaca_api_secret,
        "paper": settings.alpaca_paper,
    }
