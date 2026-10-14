"""Global lock for PyMuPDF.

MuPDF is not thread-safe, even across different documents. FastAPI runs sync
endpoints in a thread pool, so every public function that touches PyMuPDF is
wrapped with :func:`serialized` to run one at a time.
"""

from __future__ import annotations

import functools
import threading
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

MUPDF_LOCK = threading.RLock()


def serialized(fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with MUPDF_LOCK:
            return fn(*args, **kwargs)

    return wrapper
