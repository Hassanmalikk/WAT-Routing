from collections.abc import Iterator

import pytest
from django.core.cache import cache
from django.test import override_settings

from planner.clients import http


@pytest.fixture(autouse=True)
def _isolated(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(http, "BACKOFF_S", 0.0)
    cache.clear()
    with override_settings(
        TOMTOM_API_KEY="test-key", OPEN_METEO_URL="https://weather.test/v1/forecast"
    ):
        yield
    cache.clear()
