from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvName = Literal["dev", "prod"]


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields like DATABRICKS_HOST, DATABRICKS_TOKEN
    )

    app_env: EnvName = Field(
        default="dev",
        validation_alias=AliasChoices("APP_ENV", "app_env"),
    )
    catalog_name: str = Field(
        default="shared",
        validation_alias=AliasChoices("CATALOG_NAME", "catalog_name"),
    )
    schema_name: str = Field(
        default="fashion_recommendations",
        validation_alias=AliasChoices("SCHEMA_NAME", "schema_name"),
    )
    volume_path: str = Field(
        default="/Volumes/shared/fashion_recommendations/data",
        validation_alias=AliasChoices("VOLUME_PATH", "volume_path"),
    )
    warehouse_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABRICKS_WAREHOUSE_ID", "warehouse_id"),
    )

    @property
    def full_table_name(self) -> str:
        return f"{self.catalog_name}.{self.schema_name}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
