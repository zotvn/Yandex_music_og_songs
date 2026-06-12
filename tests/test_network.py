from unittest.mock import patch

import pytest

from yandex_music_og_songs.network import retry_network


def test_retry_network_succeeds_after_failure():
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise OSError(101, "Network is unreachable")
        return "ok"

    with patch("yandex_music_og_songs.network.time.sleep"):
        assert retry_network(flaky, attempts=5, label="test") == "ok"
    assert calls["count"] == 3


def test_retry_network_raises_non_retryable():
    with pytest.raises(ValueError):
        retry_network(lambda: (_ for _ in ()).throw(ValueError("bad")), attempts=3)
