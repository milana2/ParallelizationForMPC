import dataclasses as dc
from typing import NoReturn, cast, TypeVar


# https://github.com/python/mypy/issues/5818#issue-372451340
def assert_never(x: NoReturn) -> NoReturn:
    assert False, "Unhandled type: {}".format(type(x).__name__)


E = TypeVar("E")
P = TypeVar("P")


# Replace a pattern in a dataclass tree, returning the updated value
def replace_pattern(expr: E, pattern: P, replacement: P, include_lhs=True) -> E:
    if expr == pattern:
        return cast(E, replacement)
    elif isinstance(expr, list):
        return cast(
            E, [replace_pattern(e, pattern, replacement, include_lhs) for e in expr]
        )
    elif isinstance(expr, tuple):
        return cast(
            E,
            tuple(replace_pattern(e, pattern, replacement, include_lhs) for e in expr),
        )
    elif not dc.is_dataclass(expr):
        return expr
    else:
        new_params = {
            field.name: getattr(expr, field.name)
            if (not include_lhs and field.name == "lhs")
            else replace_pattern(
                getattr(expr, field.name), pattern, replacement, include_lhs
            )
            for field in dc.fields(expr)
        }
        return dc.replace(expr, **new_params)
