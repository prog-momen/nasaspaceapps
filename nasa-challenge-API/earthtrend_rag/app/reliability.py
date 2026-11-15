"""Shared request budget and Retry-After parsing; retries belong to source clients."""
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from queue import Queue, Empty
import threading
import time

_deadline = ContextVar("request_deadline", default=None)


def remaining(default: float) -> float:
    deadline = _deadline.get()
    return max(0.0, min(default, deadline - time.monotonic())) if deadline is not None else default


@contextmanager
def request_budget(seconds: float):
    current = _deadline.get()
    deadline = time.monotonic() + seconds
    token = _deadline.set(min(current, deadline) if current is not None else deadline)
    try:
        yield
    finally:
        _deadline.reset(token)


def bounded_call(fn, seconds: float):
    """Bound caller latency even for a slow trickle. Discard late HTTP responses.

    Only HTTP runs in a daemon; retries and state updates stay in the caller.
    Transport phase timeouts also remain finite. An expired outer budget prevents
    subsequent retries. The remote service may still count a timed-out request.
    """
    if seconds <= 0:
        raise TimeoutError("request deadline reached")
    q = Queue(maxsize=1)
    context = copy_context()

    def run():
        try:
            q.put((True, context.run(fn)))
        except Exception as exc:
            q.put((False, exc))

    threading.Thread(target=run, daemon=True).start()
    try:
        ok, value = q.get(timeout=seconds)
    except Empty:
        raise TimeoutError("request deadline reached") from None
    if not ok:
        raise value
    return value


def retry_after(value) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(str(value).removesuffix("s")))
    except (ValueError, TypeError):
        try:
            return max(0.0, (parsedate_to_datetime(str(value)) - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None
