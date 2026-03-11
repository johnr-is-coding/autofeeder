from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # Base config
    ENV: Literal["development", "staging", "production"] = Field(
        "development", description="Application environment"
    )
    DEBUG: bool = Field(False, description="Enable debug mode")
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    
    APP_NAME: str = Field(..., description="Application name")
    APP_VERSION: str = Field(..., description="Application version")

    # My Market News config
    MMN_BASE_URL: str = Field(..., description="Base URL for My Market News API")
    MMN_API_VERSION: str = Field(..., description="API version for My Market News API")
    MMN_API_KEY: str = Field(..., description="API key for My Market News API")

    # Scheduler config
    POLLING_INTERVAL: int = Field(15, description="Polling interval in seconds")
    POLLING_MAX_RETRIES: int = Field(3, description="Max retry attempts on failure")
    POLLING_RETRY_BACKOFF: int = Field(5, description="Seconds to wait between retries")
    DEFAULT_REQUEST_TIMEOUT: int = Field(30, description="Default HTTP request timeout in seconds")

    # Database config
    DB_SYNC_PREFIX: str = "postgresql://"
    DB_ASYNC_PREFIX: str = "postgresql+asyncpg://"
    DB_HOST: str = Field("localhost")
    DB_PORT: str = Field("5432")
    DB_USER: str = Field("postgres")
    DB_PASSWORD: str = Field("root")
    DB_NAME: str = Field("postgres")

    DB_SYNC_CONNECTION_STR: Optional[str] = None
    DB_ASYNC_CONNECTION_STR: Optional[str] = None

    DB_ECHO: bool = Field(False, description="Enable SQL query logging")
    DB_POOL_SIZE: int = Field(10, description="Number of connections in the pool")
    DB_MAX_OVERFLOW: int = Field(20, description="Max connections above pool_size")
    DB_POOL_TIMEOUT: int = Field(30, description="Seconds to wait for a connection from the pool")

    DB_EXCLUDE_SCHEMAS: str = Field("...", description="Schemas to exclude from migrations")
    DB_EXCLUDE_TABLES: str = Field("...", description="Tables to exclude from migrations")

    @model_validator(mode="after")
    def build_connection_strings(self) -> "Settings":
        self.DB_SYNC_CONNECTION_STR = (
            f"{self.DB_SYNC_PREFIX}{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
        self.DB_ASYNC_CONNECTION_STR = (
            f"{self.DB_ASYNC_PREFIX}{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
        return self

    @model_validator(mode="after")
    def set_debug_from_env(self) -> "Settings":
        if self.ENV == "development":
            self.DEBUG = True
        return self


settings = Settings()