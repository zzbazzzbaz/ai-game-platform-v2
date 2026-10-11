from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # 平台元数据库（本地 Docker PG）
    platform_database_url: str
    cors_origins: str

    # 游戏库（公网 VPS PG）：管理员凭证 + 派生规则
    pg_admin_host: str
    pg_admin_port: int
    pg_admin_user: str
    pg_admin_password: str
    pg_admin_db: str
    game_db_host: str
    game_db_port: int
    game_db_sslmode: str
    game_db_password_master_secret: str

    # 自建认证（RS256 + JWKS）
    jwt_private_key_path: str
    jwt_public_key_path: str
    jwt_issuer: str
    jwt_audience: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int

    # 内部接口
    internal_token: str

    # AGS 沙盒（E2B 协议）
    e2b_domain: str
    e2b_api_key: str
    ags_template: str
    sandbox_timeout_seconds: int

    # 腾讯云 COS
    cos_secret_id: str
    cos_secret_key: str
    cos_region: str
    cos_bucket: str
    cos_games_prefix: str

    # CloudBase 云托管（发布，M6）
    tencent_secret_id: str
    tencent_secret_key: str
    tcb_env_id: str
    tcb_region: str

    @property
    def sqlalchemy_database_url(self) -> str:
        return self.platform_database_url

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
