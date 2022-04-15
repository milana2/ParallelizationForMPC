import dataclasses as dc
from typing import NoReturn, cast, TypeVar, Callable
import networkx


# https://github.com/python/mypy/issues/5818#issue-372451340
def assert_never(x: NoReturn) -> NoReturn:
    assert False, "Unhandled type: {}".format(type(x).__name__)


E = TypeVar("E")
P = TypeVar("P")


# Replace a pattern in a dataclass tree, returning the updated value
def replace_pattern(expr: E, pattern: P, replacement: P, include_return=True) -> E:
    if expr == pattern:
        return cast(E, replacement)
    elif isinstance(expr, list):
        return cast(
            E, [replace_pattern(e, pattern, replacement, include_return) for e in expr]
        )
    elif isinstance(expr, tuple):
        return cast(
            E,
            tuple(
                replace_pattern(e, pattern, replacement, include_return) for e in expr
            ),
        )
    elif not dc.is_dataclass(expr):
        return expr
    else:
        new_params = {
            field.name: getattr(expr, field.name)
            if (not include_return and field.name == "return_value")
            else replace_pattern(
                getattr(expr, field.name), pattern, replacement, include_return
            )
            for field in dc.fields(expr)
        }
        return dc.replace(expr, **new_params)


def partially_ordered_sort(elems: list[E], ordering: Callable[[E, E], int]) -> list[E]:
    graph = networkx.DiGraph()
    for elem in elems:
        graph.add_node(elem)

    for i, e1 in enumerate(elems):
        for e2 in elems[i + 1 :]:
            if ordering(e1, e2) < 0:
                graph.add_edge(e1, e2)
            elif ordering(e1, e2) > 0:
                graph.add_edge(e2, e1)

    return list(networkx.topological_sort(graph))
