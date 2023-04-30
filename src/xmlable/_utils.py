""" Basic Utilities
Includes common helper functions for this project
- Handling optionals
- getting members by string name
"""
from typing import Any, Callable, TypeVar


T = TypeVar("T")


def some_or(data: T | None, alt: T):
    return data if data is not None else alt


N = TypeVar("N")
M = TypeVar("M")


def some_or_apply(data: N, fn: Callable[[N], M], alt: M):
    return fn(data) if data is not None else alt


def get(obj: Any, attr: str) -> Any:
    return obj.__getattribute__(attr)


def opt_get(obj: Any, attr: str) -> Any | None:
    try:
        return obj.__getattribute__(attr)
    except AttributeError:
        return None
