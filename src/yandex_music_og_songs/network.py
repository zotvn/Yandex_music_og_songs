from __future__ import annotations

import sys
import time
from typing import Callable, TypeVar

T = TypeVar("T")

_RETRY_DELAYS = (2, 4, 8, 16, 32)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in {101, 104, 110, 111}:
        return True

    name = type(exc).__name__
    if name in {"NetworkError", "ConnectionError", "TimeoutError", "ReadTimeout", "ConnectTimeout"}:
        return True

    module = type(exc).__module__ or ""
    if module.startswith("urllib3") or module.startswith("requests"):
        return True

    cause = exc.__cause__ or exc.__context__
    if cause is not None and cause is not exc:
        return _is_retryable(cause)

    return False


def retry_network(
    fn: Callable[[], T],
    *,
    attempts: int = 5,
    label: str = "запрос",
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except BaseException as exc:
            if not _is_retryable(exc):
                raise
            last_exc = exc
            if attempt >= attempts - 1:
                break
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            print(
                f"Сеть: {label} не удался, повтор через {delay}с ({attempt + 1}/{attempts})...",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)

    assert last_exc is not None
    raise last_exc
