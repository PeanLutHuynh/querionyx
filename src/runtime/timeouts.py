"""Timeout wrappers that keep runtime failures observable and recoverable."""

from __future__ import annotations

import concurrent.futures
from typing import Callable, TypeVar


T = TypeVar("T")


class StageTimeoutError(TimeoutError):
    def __init__(self, stage: str, timeout_ms: int):
        super().__init__(f"{stage} exceeded {timeout_ms} ms timeout")
        self.stage = stage
        self.timeout_ms = timeout_ms


def run_with_timeout(fn: Callable[[], T], timeout_ms: int, stage: str) -> T:
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"querionyx_{stage}")
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_ms / 1000)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise StageTimeoutError(stage, timeout_ms) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

