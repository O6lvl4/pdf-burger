"""Tests for pdf_burger.monads — verifying monad laws and combinators."""

from pdf_burger.monads import Err, IO, Ok, partition_results, pipe, safe, sequence, traverse


class TestOk:
    def test_map(self):
        assert Ok(2).map(lambda x: x * 3) == Ok(6)

    def test_bind(self):
        assert Ok(2).bind(lambda x: Ok(x + 1)) == Ok(3)

    def test_bind_to_err(self):
        result = Ok(2).bind(lambda _: Err("fail"))
        assert result == Err("fail")

    def test_unwrap(self):
        assert Ok(42).unwrap() == 42

    def test_unwrap_or(self):
        assert Ok(42).unwrap_or(0) == 42

    def test_is_ok(self):
        assert Ok(1).is_ok()
        assert not Ok(1).is_err()


class TestErr:
    def test_map_is_noop(self):
        assert Err("x").map(lambda v: v + 1) == Err("x")

    def test_bind_is_noop(self):
        assert Err("x").bind(lambda v: Ok(v)) == Err("x")

    def test_map_err(self):
        assert Err("x").map_err(lambda e: e.upper()) == Err("X")

    def test_unwrap_or(self):
        assert Err("x").unwrap_or(99) == 99

    def test_is_err(self):
        assert Err("x").is_err()
        assert not Err("x").is_ok()


class TestMonadLaws:
    """Verify the three monad laws for Result."""

    def test_left_identity(self):
        # return a >>= f  ==  f a
        f = lambda x: Ok(x + 1)
        assert Ok(5).bind(f) == f(5)

    def test_right_identity(self):
        # m >>= return  ==  m
        assert Ok(5).bind(Ok) == Ok(5)

    def test_associativity(self):
        # (m >>= f) >>= g  ==  m >>= (λx → f x >>= g)
        f = lambda x: Ok(x + 1)
        g = lambda x: Ok(x * 2)
        m = Ok(3)
        assert m.bind(f).bind(g) == m.bind(lambda x: f(x).bind(g))


class TestIO:
    def test_pure(self):
        assert IO.pure(42).run() == 42

    def test_map(self):
        assert IO.pure(2).map(lambda x: x * 3).run() == 6

    def test_bind(self):
        result = IO.pure(2).bind(lambda x: IO.pure(x + 1)).run()
        assert result == 3

    def test_lazy_execution(self):
        calls = []
        io = IO(lambda: calls.append(1) or 42)
        assert len(calls) == 0
        io.run()
        assert len(calls) == 1


class TestSafe:
    def test_success(self):
        result = safe(lambda: 42)()
        assert result == Ok(42)

    def test_exception(self):
        result = safe(lambda: 1 / 0)()
        assert result.is_err()
        assert isinstance(result.error, ZeroDivisionError)


class TestCombinators:
    def test_pipe(self):
        result = pipe(2, lambda x: x + 1, lambda x: x * 3)
        assert result == 9

    def test_sequence_all_ok(self):
        assert sequence([Ok(1), Ok(2), Ok(3)]) == Ok([1, 2, 3])

    def test_sequence_with_err(self):
        result = sequence([Ok(1), Err("fail"), Ok(3)])
        assert result == Err("fail")

    def test_traverse_all_ok(self):
        result = traverse(lambda x: Ok(x * 2), [1, 2, 3])
        assert result == Ok([2, 4, 6])

    def test_traverse_with_err(self):
        result = traverse(lambda x: Err("no") if x == 2 else Ok(x), [1, 2, 3])
        assert result == Err("no")

    def test_partition_results(self):
        oks, errs = partition_results([Ok(1), Err("a"), Ok(2), Err("b")])
        assert oks == [1, 2]
        assert errs == ["a", "b"]
