"""Lightweight monads for functional error handling and composition.

Provides Result (Either), IO, and combinators — no external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Callable, Generic, TypeVar, overload

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


# ── Result monad (Either) ──────────────────────────────────────────


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def map(self, f: Callable[[T], U]) -> Ok[U]:
        return Ok(f(self.value))

    def bind(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return f(self.value)

    def map_err(self, _f: Callable[[E], E]) -> Ok[T]:
        return self

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, _default: T) -> T:
        return self.value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def map(self, _f: Callable) -> Err[E]:
        return self

    def bind(self, _f: Callable) -> Err[E]:
        return self

    def map_err(self, f: Callable[[E], E]) -> Err[E]:
        return Err(f(self.error))

    def unwrap(self):
        raise RuntimeError(f"unwrap called on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        return default

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True


type Result[T, E] = Ok[T] | Err[E]


def safe(f: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
    """Decorator: wrap exceptions into Err, return values into Ok."""
    def wrapper(*args, **kwargs) -> Result[T, Exception]:
        try:
            return Ok(f(*args, **kwargs))
        except Exception as e:
            return Err(e)
    return wrapper


# ── IO monad ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class IO(Generic[T]):
    """Lazy IO action. The effect runs only when .run() is called."""
    _effect: Callable[[], T]

    def run(self) -> T:
        return self._effect()

    def map(self, f: Callable[[T], U]) -> IO[U]:
        return IO(lambda: f(self.run()))

    def bind(self, f: Callable[[T], IO[U]]) -> IO[U]:
        return IO(lambda: f(self.run()).run())

    @staticmethod
    def pure(value: T) -> IO[T]:
        return IO(lambda: value)


# ── Combinators ────────────────────────────────────────────────────


def pipe(value: T, *fns: Callable) -> T:
    """Thread a value through a sequence of functions left-to-right."""
    return reduce(lambda acc, f: f(acc), fns, value)


def sequence(results: list[Result[T, E]]) -> Result[list[T], E]:
    """Collect a list of Results into a Result of list. Short-circuits on first Err."""
    return reduce(
        lambda acc, r: acc.bind(lambda xs: r.map(lambda x: [*xs, x])),
        results,
        Ok([]),
    )


def traverse(f: Callable[[T], Result[U, E]], items: list[T]) -> Result[list[U], E]:
    """Map a function over items and sequence the results."""
    return sequence(list(map(f, items)))


def partition_results(results: list[Result[T, E]]) -> tuple[list[T], list[E]]:
    """Split results into (successes, failures) without short-circuiting."""
    oks = [r.value for r in results if r.is_ok()]
    errs = [r.error for r in results if r.is_err()]
    return oks, errs
