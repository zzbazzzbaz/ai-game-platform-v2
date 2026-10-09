from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    s3_endpoint_url: str
    s3_bucket: str
    s3_path_style: bool
    s3_access_key: str
    s3_secret_key: str
    modal_token_id: str
    modal_token_secret: str
    modal_app: str
    modal_image_tag: str
    modal_idle_timeout_seconds: int
    modal_timeout_seconds: int
    auth_secret: str
    auth_internal_token: str
    auth_token_ttl_seconds: int
    public_game_base_url: str
    cors_origins: str

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sqlalchemy_database_url(self) -> str:
        return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
