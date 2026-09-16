import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_and_blank_url():
    assert Settings().database_url is None
    assert Settings(database_url="").database_url is None
    assert Settings().db_connect_timeout == 5


@pytest.mark.parametrize("url", ["broken", "sqlite:///db", "postgresql://host/db"])
def test_invalid_urls(url):
    with pytest.raises(ValidationError):
        Settings(database_url=url)


def test_environment_overrides_dotenv(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("APP_ENV=development\n", encoding="utf-8")
    monkeypatch.setenv("APP_ENV", "test")
    assert Settings().app_env == "test"


def test_secret_is_hidden():
    settings = Settings(database_url="postgresql+psycopg://user:private@localhost/db")
    assert "private" not in repr(settings)
    with pytest.raises(ValidationError) as error:
        Settings(database_url="sqlite://user:private@localhost/db")
    assert "private" not in str(error.value)


@pytest.mark.parametrize("timeout", [0, 31])
def test_bounded_timeout(timeout):
    with pytest.raises(ValidationError):
        Settings(db_connect_timeout=timeout)
