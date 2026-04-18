import os

from app.core.config import Settings


def test_settings_reads_jwt_secret_from_env() -> None:
    os.environ["JWT_SECRET"] = "test-secret-value"
    settings = Settings()
    assert settings.jwt_secret == "test-secret-value"


def test_settings_database_url_defaults_to_sqlite() -> None:
    os.environ["JWT_SECRET"] = "x"
    settings = Settings()
    assert settings.database_url.startswith("sqlite+aiosqlite:///")


def test_settings_brapi_token_optional() -> None:
    os.environ["JWT_SECRET"] = "x"
    os.environ.pop("BRAPI_TOKEN", None)
    settings = Settings()
    assert settings.brapi_token is None
