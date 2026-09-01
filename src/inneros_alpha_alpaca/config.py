from __future__ import annotations

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    alpaca_paper: bool = Field(default=True, alias="ALPACA_PAPER")
    alpaca_api_base: HttpUrl = Field(default="https://paper-api.alpaca.markets", alias="ALPACA_API_BASE")
    alpaca_key_id: str = Field(default="", alias="ALPACA_KEY_ID")
    alpaca_secret_key: str = Field(default="", alias="ALPACA_SECRET_KEY")
    inneros_reasoning_url: str = Field(default="http://127.0.0.1:8000/v1", alias="INNEROS_REASONING_URL")
    inneros_mongo_uri: str = Field(default="", alias="INNEROS_MONGO_URI")
    inneros_mongo_db: str = Field(default="inneros_alpha_alpaca", alias="INNEROS_MONGO_DB")
    max_notional_usd: float = Field(default=2500.0, alias="MAX_NOTIONAL_USD")
    max_qty: float = Field(default=25.0, alias="MAX_QTY")
    allowed_symbols: str = Field(default="SPY,QQQ,AAPL,MSFT,NVDA,AMD", alias="ALLOWED_SYMBOLS")

    @property
    def normalized_api_base(self) -> str:
        return str(self.alpaca_api_base).rstrip("/")

    @property
    def symbol_allowlist(self) -> set[str]:
        return {item.strip().upper() for item in self.allowed_symbols.split(",") if item.strip()}

    def alpaca_headers(self) -> dict[str, str]:
        if not self.alpaca_key_id or not self.alpaca_secret_key:
            return {}
        return {
            "APCA-API-KEY-ID": self.alpaca_key_id,
            "APCA-API-SECRET-KEY": self.alpaca_secret_key,
        }
