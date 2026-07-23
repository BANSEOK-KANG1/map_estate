from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    onbid_service_key: str = ""
    molit_service_key: str = ""
    kakao_rest_key: str = ""
    # Optional override only — 정비사업은 기본으로 MOLIT_SERVICE_KEY 재사용
    data_go_kr_service_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/auction.db"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:49693,http://127.0.0.1:49693,*"
    )
    host: str = "0.0.0.0"
    port: int = 8001

    @property
    def redev_service_key(self) -> str:
        return (self.data_go_kr_service_key or self.molit_service_key or "").strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
