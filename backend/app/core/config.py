"""Environment configuration; database credentials are never logged."""

from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def canonical_hostname(hostname: str) -> str | None:
    try:
        address = ip_address(hostname)
    except ValueError:
        if (
            not hostname.isascii()
            or len(hostname) > 253
            or hostname.replace(".", "").isdigit()
        ):
            return None
        labels = hostname.split(".")
        if any(
            not 1 <= len(label) <= 63
            or not label[0].isalnum()
            or not label[-1].isalnum()
            or any(not (character.isalnum() or character == "-") for character in label)
            for label in labels
        ):
            return None
        return hostname
    return f"[{address.compressed}]" if address.version == 6 else str(address)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = None
    db_connect_timeout: int = Field(default=5, ge=1, le=30)
    session_ttl_minutes: int = Field(default=60, ge=1, le=1440)
    # ST-047: depot of every optimization (WGS84). The default is the spike's
    # working assumption (Santa Anita, ECL-93); set the company's real depot
    # with DEPOSITO_LATITUD / DEPOSITO_LONGITUD. It is kept in each snapshot.
    deposito_latitud: float = Field(default=-12.0470, ge=-90, le=90)
    deposito_longitud: float = Field(default=-76.9680, ge=-180, le=180)
    # RNF-001: the search stops here; the request stays well under 45 s.
    optimizacion_tiempo_limite_s: int = Field(default=20, ge=1, le=40)
    cors_allowed_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(
        cls, origins: list[str], info: ValidationInfo
    ) -> list[str]:
        normalized: list[str] = []
        for origin in origins:
            try:
                parsed = urlsplit(origin)
                hostname = parsed.hostname
                port = parsed.port
            except ValueError:
                raise ValueError("Invalid CORS origin") from None

            if (
                parsed.scheme not in {"http", "https"}
                or not hostname
                or "\\" in origin
                or parsed.netloc.endswith(":")
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or "*" in origin
                or any(character.isspace() for character in origin)
            ):
                raise ValueError("Invalid CORS origin")

            canonical_host = canonical_hostname(hostname)
            if canonical_host is None:
                raise ValueError("Invalid CORS origin")
            if (parsed.scheme, port) in {
                ("http", 80),
                ("https", 443),
            }:
                raise ValueError("Invalid CORS origin")
            canonical_netloc = canonical_host
            if port is not None:
                canonical_netloc = f"{canonical_host}:{port}"
            exact_origin = f"{parsed.scheme}://{canonical_netloc}"
            if origin not in {exact_origin, f"{exact_origin}/"}:
                raise ValueError("Invalid CORS origin")
            if info.data.get("app_env") == "production" and parsed.scheme != "https":
                raise ValueError("Production CORS origins must use HTTPS")
            if exact_origin in normalized:
                raise ValueError("Duplicate CORS origin")
            normalized.append(exact_origin)
        return normalized

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_url(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("database_url")
    @classmethod
    def validate_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return value
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError:
            raise ValueError("Invalid database URL") from None
        if url.drivername != "postgresql+psycopg" or not url.host or not url.database:
            raise ValueError("Use postgresql+psycopg with host and database")
        return value
